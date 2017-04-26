# Augur Developer Metrics

Help team leads, managers and developers track progress, improvement, 
gaps by combing data from multiple tools into an easy to use dashboard
using the Augur Development Method.

This is a library that can be easily included into any client that wants to
collect data using ADM.  

# Augur Installation

Augur is hosted in the UA Artifactory PyPI index because it contains some UA-specific
 information (currently).  Access to only the pypi index on the artifactory host is given
 to the following artifactory user: `pypi-reader`

To install, you can do one of the following:

## Install on command line

    pip install augur -i https://pypi-reader:ThOgrAVultiA@artifacts.ua-ecm.com/artifactory/api/pypi/ua-pypi/simple

Without changing your global index, this will install augur using the custom index this once.

## Install in requirements.txt

Modify you requirements.txt file by including this at the top of the file:

    --extra-index-url https://pypi-reader:ThOgrAVultiA@artifacts.ua-ecm.com/artifactory/api/pypi/ua-pypi/simple

Then include augur as you would any other package:

    augur==<version>
    or
    augur

# Augur Development

To upload a new version of augur, you can modify your .pypirc file with the following:

    [dist-utils]
    .... # whatever indexes you already had in there
    local

    ...

    [local]
    repository: https://artifacts.ua-ecm.com/artifactory/api/pypi/ua-pypi
    username: <username> # must have publish rights
    password: <password>


Then build and upload the new version from within the augur root directory:

    python setup.py sdist upload -r local


# Augur Integration

## Settings

In order to use Augur there are some settings that it expects to be accessible
via environment variables.  In some cases, there are defaults that are applied,
in other cases, the initialization will fail if not specified.


| Environment Variable |  Purpose                                 |   Default   | Example                        |
| -------------------- |:-----------------------------------------|:----------: |--------------------------------|
| JIRA_INSTANCE        | The full url to the JIRA instance to use | Required    | http://voltron.atlassian.net/   |
| JIRA_USERNAME        | The full url to the JIRA instance to use | Required    | A username   |
| JIRA_PASSWORD        | The full url to the JIRA instance to use | Required    | It's a password   |
| JIRA_API_PATH        | The relative path to the root of the rest endpoints | rest/api/2 | rest/api/2  |
| CONFLUENCE_INSTANCE  | The full url to the Confluence instance  | JIRA_INSTANCE    | http://voltron.atlassian.net/wiki   |
| CONFLUENCE_USERNAME  | The full url to the Confluence instance  | JIRA_USERNAME    | A username   |
| CONFLUENCE_PASSWORD  | The full url to the Confluence instance  | JIRA_PASSWORD    | Another password   |
| GITHUB_BASE_URL  | The full url to the Github instance  | Required    | http://github.com/ |
| GITHUB_LOGIN_TOKEN  | The token of the user that should be used to access the API for the instance of github specificed in GITHUB_BASE_URL | Required    | cbab75c171843afef555d9dcbc212e0b54681b32 |
| GITHUB_CLIENT_ID | The client ID that has been registered for the client that is using this instance of the Augur library | Required    | e3d808650b4f45f9ac03 |
| GITHUB_CLIENT_SECRET | The client secret that has been registered for the client that is using this instance of the Augur library | Required    | f3d80e650b4d45f9ad15 |


# Augur Tool Setup
Augur currently works with Github and Jira and makes certain assumptions about
how both are setup.  As of now, these assumptions are not enforced by Augur. They
must be manually enforced by the administrator.

## Github

There is no explicit requirements for Github setup other than this: Augur was developed from the enterprise edition 
 which means it's more acceptable for Github Organizations to be part of the hierarchy of the codebase.  

## Jira 

### Teams
This assumes that agile teams developers are all members of the Jira instance with 
their own account.  Additionally, it assumes that the teams are represented
in Jira with Jira "Groups".   Each Team Group musth have the format 
"Team <team_name>".  This is to ensure that groups are not pulled into the 
metrics that are not meant for Augur analytics.

This also assumes that there is exactly one Agile Board associated with a 
 team and the sprints for that team are managed through that board.

### Sprint
Like groups, Sprint names must follow a certain format: 

    <sprint_num> - Team <team_name>
    
    Example:
    001 - Team Voltron
    
This is to ensure that only sprints that are associated with the team are
included in the metrics.  Due to the way Jira works, it is possible for a 
sprint that is part of a different agile board to be included in the metrics
if this formatting restriction is not used.

### Workflow
Augur also assumes a specific workflow within Jira that is used across all projects
that are to be monitored The workflow includes the following status:

* Open (Open State)
* In Progress (In Progress State)
* Quality Review (In Progress State)
* Staging (In Progress State)
* Production (In Progress State)
* Resolved (Resolution State)

### Deployment
If using the Jira hook that enables the automatic creation and linking of work tickets
with CM tickets, then a few things are assumed as well:

* A project exists with the key "CM" that has the following statuses:
    * Ready for Planning (Open State)
    * Staging Pending (In Progress State)
    * Staging Deployed (In Progress State)
    * Staging Validated (In Progress State)
    * Production Pending (In Progress State)
    * Production Validated (In Progress State)
    * Production Deployed (Resolution State)
    * Abandoned (Resolution State)
* The following custom field exists: "Deployment Status" and it has the following options
    * Pending
    * Deployed
    * Validated