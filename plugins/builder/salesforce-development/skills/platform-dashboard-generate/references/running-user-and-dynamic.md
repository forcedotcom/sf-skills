# Running User, Dynamic Dashboards, Folders

Every dashboard runs its reports as **some** user. Choose deliberately: a static dashboard shows every
viewer the running user's data, which may be more than they could normally see.

| UI ("View Dashboard As") | `dashboardType` | `runningUser` | Counts toward dynamic limit |
|--------------------------|-----------------|---------------|-----------------------------|
| Me / Another person | `SpecifiedUser` | that user's username (omit = deploying user) | No |
| …and "Let authorized users change running user" | `MyTeamUser` | the default user | **Yes** |
| The dashboard viewer | `LoggedInUser` | ignored | **Yes** |

- `MyTeamUser` is how metadata expresses "viewers can switch whose view they see": people with
  *View My Team's Dashboards* can pick anyone below them in the role hierarchy, *View All Data* anyone.
- **Unknown `runningUser` fails the deploy**: "Cannot find a user that matches any of the following
  usernames: …". Omit the element to run as the deploying user.
- **Sandbox suffixes are handled for you.** Retrieve writes usernames without the sandbox suffix
  (`jo@acme.com`), and deploy to a sandbox tries `jo@acme.com.<sandbox>` automatically, so production
  files deploy to sandboxes unchanged.

## Dynamic dashboard limit

`LoggedInUser` + `MyTeamUser` dashboards per org: Enterprise **5**, Unlimited/Performance **10**,
Developer **3**. Over the limit: **"You reached the limit for dashboards run as the logged-in user."**

- **Deleted dynamic dashboards keep counting while they sit in the recycle bin** (up to 15 days).
  Purging frees the slot but is permanent: tell the user, get an explicit yes, then select only the
  named dashboards in Recycle Bin and choose Delete. Never use "Empty Org Recycle Bin".
- Check headroom without using a slot: validate instead of deploy
  (`sf project deploy validate …`) — validation fails with the same message when the org is full.
- Count current ones: `SELECT Type, COUNT(Id) FROM Dashboard GROUP BY Type` (deleted ones are not listed).
- Dynamic dashboards cannot be subscribed to or have scheduled refreshes, and cannot live in a
  private folder.

## Folders and sharing

```xml
<?xml version="1.0" encoding="UTF-8"?>
<DashboardFolder xmlns="http://soap.sforce.com/2006/04/metadata">
    <folderShares>                               <!-- optional: add only the audience the user asked for -->
        <accessLevel>View</accessLevel>          <!-- View | EditAllContents | Manage -->
        <sharedTo>Sales_Managers</sharedTo>      <!-- group/role developer name, or username -->
        <sharedToType>Group</sharedToType>       <!-- Group | Role | RoleAndSubordinates | RoleAndSubordinatesInternal | User | … -->
    </folderShares>
    <name>Sales Dashboards</name>
</DashboardFolder>
```

- **Sharing is the exposure decision.** Everyone a folder is shared with sees the running user's data on
  every static dashboard in it. Create new folders with **no** `folderShares` and add exactly the
  audience the user names. Never add `AllInternalUsers`, `Organization` or portal audiences on your own
  initiative. `validate_dashboard.py <folder file>` warns on those.

- File: `dashboards/<FolderDevName>.dashboardFolder-meta.xml`; dashboards go in `dashboards/<FolderDevName>/`.
- A folder with no `folderShares` deploys (visible to its owner and admins).
- UI levels: Viewer = `View`, Editor = `EditAllContents`, Manager = `Manage`.
- Deploy the folder with (or before) its first dashboard; a failed deploy rolls back a new folder.

## Naming

- Dashboards built in the editor get random 30-letter DeveloperNames (`xQbTnLwYzKdRpHsVmCgJfAeUoIiNkP`);
  the visible name is `<title>`. Give generated dashboards readable DeveloperNames (`Sales_Pipeline`).
- Dashboard Ids start with **01Z** (copy them from the URL). Some help articles say `0FK` — that is wrong
  for Lightning dashboards.
