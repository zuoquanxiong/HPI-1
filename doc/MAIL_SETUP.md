This is a distillation of the steps described in [this issue](https://github.com/purarue/HPI/issues/15)

There are two mail parsing modules here -- `my.mail.imap` and `my.mail.mbox`. An [`mbox` file](https://docs.python.org/3/library/mailbox.html) is just a collection of email messages in a single text file

You can also use both modules at the same time -- see `my.mail.all` below

Remember to first run: `hpi module install my.mail.imap` to install the necessary dependencies

Note: There are _lots of_ different ways email clients/websites will export messages, so any mention of thunderbird add-ons or syncing tools used in particular to back up mail are just examples. Anything that gives you access to either the raw email files or an mbox should do.

## `my.mail.imap`

Personally, I use `my.mail.imap`. To sync my mail, I use [`mutt-wizard`](https://github.com/LukeSmithxyz/mutt-wizard/), which uses `mbsync` under the hood to saves a bunch of individual mail files in `~/.local/share/mail` -- updating every 5 minutes.

There are - of course - hundreds of ways to save your mail locally. Lets take [the ImportTools thunderbird add-on](https://addons.thunderbird.net/en-US/thunderbird/addon/importexporttools-ng/) as an example (since its the one we did troubleshooting on in the [issue](https://github.com/purarue/HPI/issues/15)). To match the format `my.mail.imap` expects, select the folder you want to export, then use `Tools > ImportExportToolsNg > Export all messages in the Folder > Plain Text Format`, and export it to a folder somewhere. Then, in your config file, setup the block to point it at that path:

```python
class mail:
    class imap:
        # path[s]/glob to the the mailboxes/IMAP files
        # you could also do something like:
        # mailboxes = "~/Documents/mbsync/*@*"
        # to match any files in that directory with '@' in them
        mailboxes = "~/Documents/ExportPlaintext/"

        # filter function which filters the input paths
        filter_path: Optional[Callable[[Path], bool]]
```

To verify its finding your files, you can use `hpi query my.mail.imap.files -s` -- that'll print all the matched files

That may be fine to parse an archive (a backup of some email you don't use anymore), but you need to continuously create new archives/delete old ones.

Recently, ImportToolsExports has added support for periodic backups, but only in MBOX format. So -->

## `my.mail.mbox`

If you already have access to an mbox file, you can skip this setup, is just an example:

### Thunderbird add-on

In `Tools > ImportExportToolsNg > Options > Backup scheduling`, set the `Destination` and `Enable Frequency` to backup once per day, selecting `Just mail files`

You can force a backup with `Tools > ImportExportToolsNg > Backup`

Note: you can set the `Overwrite the mbox files with the same name in the destination directory` to overwrite your backup. Alternatively, since `my.config` is a python script, you could write some custom python function to parse the timestamp from the exported filepath, and then pass those to `mailboxes` in your `my.config`, using only using the latest exports as the input. Though, If you're overwriting the `mbox` files while HPI is trying to parse the files, HPI may fail.

### Setup mbox

Once you've exported, setup your configuration to point at the directory. Note that since this uses `my.mail.imap` to parse the messages, you may have to setup a basic config with no files so that module does not fail:

```python
class mail:

    class imap:
        # signifies no files
        mailboxes = ''

    class mbox:

        # paths/glob to the mbox directory -- searches recursively
        mailboxes = "~/Documents/mboxExport"

        # additional extensions to ignore
        exclude_extensions = (".sbd")
```

## `my.mail.all`

You can also use both of these at the same time -- if you have some exported as individual text files and others as mbox files, setup a config like above, specifying `mailboxes` from both `imap` and `mbox`

Then -- you can just use the `my.mbox.all.mail` function, which returns unique messages from both sources

## Testing

To make sure this works, you can use the `doctor` and `query` commands, to make sure there are no config errors and it parses your mail properly:

```bash
hpi --debug doctor --verobose my.mail.all
hpi --debug doctor --verbose my.mail.imap
hpi --debug doctor --verbose my.mail.mbox
```

```bash
hpi --debug query my.mail.all --stream
hpi --debug query my.mail.imap --stream
hpi --debug query my.mail.mbox --stream
```
