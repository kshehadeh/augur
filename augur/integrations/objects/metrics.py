import datetime
from munch import Munch, munchify
import logging
from augur import common
import pandas


class Metrics(object):
    def __init__ (self, context):
        self.context = context
        self.logger = logging.getLogger("augurjira")


class IssueCollectionMetrics(Metrics):

    def __init__(self, context, collection):
        self.collection = collection
        super(IssueCollectionMetrics, self).__init__(context)

    def status_analysis(self, options=None):
        status_counts = {
            'remaining_ticket_count': 0
        }

        for issue in self.collection:
            status_as_key = common.status_to_dict_key(issue.status)
            if status_as_key not in status_counts:
                status_counts[status_as_key] = 0
            status_counts[status_as_key] += 1

            if not self.context.workflow.is_resolved(issue.status, issue.resolution):
                status_counts['remaining_ticket_count'] += 1

        return munchify(status_counts)

    def timing_analysis(self, options=None):
        """
        For each issue in the collection, this will create an item a dictionary keyed on the issue key
        for each issue with the value being a dictionary containing the start, end and total times for each
        status along with the full in progress time.
        :param options: ----no options----
        :return: As follows:
            {
                'statuses': {
                    'status1': {
                        total: <timedelta>,
                        start: <datetime>,
                        end: <datetime>,
                    },
                    ...
                },
                'total_in_seconds': <float>,
                'total_as_time_delta': <timedelta>
            }
        """

        issues_with_timing = {}
        for issue in self.collection:
            # initialize all the keys for stats
            timing = {
                'statuses': {},
                'total_in_seconds': 0.0,
                'total_as_time_delta': None
            }
            for s in self.context.workflow.in_progress_statuses():
                s_as_key = common.status_to_dict_key(s)
                t = common.get_issue_status_timing_info(issue.issue, s)
                timing[s_as_key] = {
                    'total':t['total_time'],
                    'start':t['start_time'],
                    'end':t['end_time']
                }
                timing['total_in_seconds'] += t['total_time'].total_seconds()

            timing['total_as_time_delta'] = datetime.timedelta(seconds=timing['total_in_seconds'])
            issues_with_timing[issue.key] = (munchify(timing))

        return munchify(issues_with_timing)

    def point_analysis(self, options=None):
        """
        Does a very general analysis of a collection of issues
        :param options:
                - total_only (Boolean): If True, then issue details will not be included in many of the results -
                        just the totals
        :return: As follows:
        {
            'tickets': {
                'total_ticket_count': <integer>,
                'incomplete_ticket_count': <integer>,
                'unpointed_ticket_count': <integer>,
            }
            'points': {
                "total_points": 0.0,
                "completed_points": 0.0,
                "incomplete_points": 0.0,
                "percent_complete_points": 0,
                "abandoned_points": 0.0,
            },
            'developers': {
                'username': {
                    "info": <username>,
                    "complete_points": 0,
                    "incomplete_points": 0,
                    "abandoned_points": 0,
                    "percent_complete_points": 0,
                    'issues': []
                },
                ...
            }
        }
        """

        options = munchify(options)

        # Initialize the general analytics
        result = Munch({
            "ticket_count": self.collection.count(),
            "remaining_ticket_count": 0,
            "unpointed": 0.0,
            'developer_stats': {},
            'issues': {},
        })

        # Initialize the status counters
        result.update({common.status_to_dict_key(x): 0 for x in self.context.workflow.statuses})

        # Initialize point totals
        result.update({
            "complete": 0.0,
            "incomplete": 0.0,
            "total_points": 0.0,
            "percent_complete": 0,
            "abandoned": 0.0,
        })

        for issue in self.collection:
            assignee_cleaned = common.clean_username(issue.assignee)

            if issue.assignee not in result['developer_stats']:
                result['developer_stats'][assignee_cleaned] = Munch({
                    "info": issue.assignee,
                    "complete": 0,
                    "incomplete": 0,
                    "abandoned": 0,
                    "percent_complete": 0,
                    'issues': []
                })

            # Add this issue to the list of issues for the user
            result['developer_stats'][assignee_cleaned]['issues'].append(issue.key)

            if self.context.workflow.is_resolved(issue.status, issue.resolution):
                result['complete'] += issue.points
                result['developer_stats'][assignee_cleaned]['complete'] += issue.points

            elif self.context.workflow.is_abandoned(issue.status, issue.resolution):
                result["abandoned"] += issue.points
                result['developer_stats'][assignee_cleaned]['abandoned'] += issue.points

            else:
                result["incomplete"] += issue.points
                result['developer_stats'][assignee_cleaned ]['incomplete'] += issue.points

            if not issue.points and not self.context.workflow.is_abandoned(issue.status, issue.resolution):
                result['unpointed'] += 1

        total_points = result['complete'] + result['incomplete'] + result['abandoned']
        result["percent_complete"] = int(((result['complete'] / total_points) if total_points > 0 else 0) * 100.0)
        result['total_points'] = total_points

        # get dev specific stats
        for assignee, dev in result['developer_stats'].iteritems():
            total = dev['complete'] + dev['incomplete'] + dev['abandoned']
            dev['percent_complete'] = int((dev['complete'] / total if total > 0 else 0) * 100.0)
            dev['total_points'] = total

        return munchify(result)

    def get_data_frame(self, data_to_include=()):
        """

        :param data_to_include: This is a list or tuple containing zero or more of the following keys:
            timing, points, statuses

        :return: Returns a pandas DataFrame
        """
        data = []

        timing_analysis = None
        point_analysis = None
        if 'timing' in data_to_include:
            timing_analysis = self.timing_analysis()

        if 'points' in data_to_include:
            point_analysis = self.point_analysis()

        if 'points' in data_to_include:
            statuses = self.status_analysis()

        for issue in self.collection:
            row = {
                "issuetype": issue.issuetype,
                "assignee": issue.assignee,
                "points": issue.points,
                "dev_team": issue.team_name,
                "description_length": len(issue.description),
                "reporter": issue.reporter
            }

            # now add columns for each time_<status> with the value being the number of seconds that the ticket
            #   was in that status.
            for status,timing_info in timing_analysis.statuses:
                in_seconds = timing_info['total'].total_seconds() if \
                    isinstance(timing_info['total'], datetime.timedelta) else 0.0

                row["time_%s" % status] = in_seconds

            data.append(row)

        return pandas.DataFrame(data=data)

class BoardMetrics(Metrics):
    def __init__(self, context, board):
        self._board = board
        super(BoardMetrics, self).__init__(context)

    def backlog_analysis(self, options=None):

        if not self._board or not self._board.option('include_sprint_reports'):
            self.logger.error("Board Metrics: The board object given must include sprint reports in order to "
                              "generate metrics")
            return False

        collection = self._board.get_backlog()

        metrics = {
            "points":{
                "unpointed":[],
                # pointed stories will be grouped by number of points keyed on their point value converted to string
            },
            "grade":""
        }

        pointed = 0
        unpointed = 0

        for issue in collection.issues:

            if not issue.points:
                metrics['points']['unpointed'].append(issue.key)
                unpointed += 1
            else:
                pointed += 1
                key = str(issue.points)
                if key not in metrics['points']:
                    metrics['points'][key] = []

                metrics['points'][key].append(issue.key)

        total = pointed+unpointed
        if total > 0:
            percentage = (float(pointed)/float(total))*100.0
        else:
            percentage = 0.0

        metrics['total_unpointed_tickets'] = unpointed
        metrics['total_pointed_tickets'] = pointed
        metrics['pointed_percentage'] = percentage

        # now look at velocity for that board
        # sprints = self.get_sprints_from_boardby_team(team)

        if percentage >= 90.0:
            grade = "A"
        elif percentage >= 80.0:
            grade = "B"
        elif percentage >= 70.0:
            grade = "C"
        elif percentage >= 60.0:
            grade = "D"
        else:
            grade = "E"

        metrics['grade'] = grade

        return munchify(metrics)

    def historic_sprint_analysis(self, options=None):
        """
        Analyzes all the sprints in the given board.
        :param options: No options at this time.
        :return: Returns a munchified dictionary containing aggregate metrics.
        """

        sprint_collection = self._board.get_sprints()
        overall_metrics_list = []
        for sprint in sprint_collection:
            tp = (sprint.name, sprint.completed_points, sprint.incomplete_points, sprint.average_point_size)
            overall_metrics_list.append(tp)

        df_sprints = pandas.DataFrame(overall_metrics_list, columns=[
            "Name","Points Completed","Incomplete Points","Average Point Size"])

        avg_velocity = df_sprints["Points Completed"].mean()
        low_velocity = df_sprints["Points Completed"].min()
        high_velocity = df_sprints["Points Completed"].max()
        avg_point_size = df_sprints["Average Point Size"].mean()
        highest_avg_point_size = df_sprints["Average Point Size"].max()
        lowest_avg_point_size = df_sprints["Average Point Size"].min()

        return munchify({
            "avg_velocity": avg_velocity,
            "low_velocity": low_velocity,
            "high_velocity": high_velocity,
            "avg_point_size": avg_point_size,
            "highest_avg_point_size": highest_avg_point_size,
            "lowest_avg_point_size": lowest_avg_point_size
        })

