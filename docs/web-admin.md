# Web Admin

[简体中文](web-admin.zh.md) | English

This branch adds an optional web admin interface inside the existing bot process. It uses the same database, feed monitoring, and Telegram delivery pipeline as the bot. The interface supports Chinese and English, with light and dark themes.

This is a **superadministrator interface for one bot instance**. Anyone with the admin secret can view and edit all private-chat, channel, and group subscriptions stored by that instance. It does not manage other people's bots or multiple bot tokens.

## Setup

Keep your existing deployment settings, including `TOKEN` and `MANAGER`, and add the following to `.env`:

```dotenv
WEB_ADMIN_TOKEN=replace-with-a-random-secret-at-least-32-characters
WEB_ADMIN_HOST=127.0.0.1
WEB_ADMIN_PORT=8080
```

Generate a random secret with:

```console
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Start the bot as usual with `python telegramRSSbot.py`. Open `http://127.0.0.1:8080` and enter your admin secret.

If `WEB_ADMIN_TOKEN` is unset, the admin server does not listen on any port. A token shorter than 32 characters causes startup to fail. The browser keeps the token only in the current page's memory; reloading the page requires signing in again.

### Docker

Copy `docker-compose.web.yml.sample` to `docker-compose.web.yml`, prepare `.env` with your bot settings and admin secret, then run:

```console
docker compose -f docker-compose.web.yml up -d --build
```

Build **this branch**: upstream images do not contain these features. The example listens on `0.0.0.0` inside the container but publishes port 8080 only on the host's loopback address.

For remote access, forward the port over SSH:

```console
ssh -L 8080:127.0.0.1:8080 user@server
```

Then open `http://127.0.0.1:8080` on your own computer. If you expose the admin interface through a reverse proxy, configure HTTPS and keep the page and API on the same origin.

## Subscriptions and destinations

Use the language selector and theme button at the top of the page to switch between Chinese/English and light/dark mode. Your choices are remembered in this browser; on first visit, the page uses your browser language and system color preference. These preferences do not change bot settings or backup contents.

When Chinese is selected, the navigation labels are:

| Interface label | Meaning |
| --- | --- |
| 订阅源 | Subscriptions |
| 接收目标 | Destinations: private chats, channels, and groups |
| 全局配置 | Global settings |
| 备份与还原 | Backup and restore |

### Manage subscriptions

The **Subscriptions / 订阅源** page groups subscriptions by destination. Each group shows its subscription and active counts; click its heading to collapse or expand it. Search and destination/status filters apply across groups, and matching groups expand automatically when searching or filtering by destination. You can search, filter by destination or status, add, delete, pause, enable, and edit subscriptions.

Choose **添加订阅** to add an RSS URL and destination. Choose **编辑** on an existing subscription to change its custom title, tags, polling interval, message formatting, or keyword rules. An empty title uses the feed's title. Separate tags with spaces. An empty polling interval inherits the destination's default.

The RSS URL and destination identify a subscription and cannot be changed in the edit form. To change either, add the replacement subscription and then delete the old one.

### Add destinations and edit defaults

Private-chat users must first send `/start` to the bot in Telegram. For a channel or group, add the bot and grant the permissions needed to send messages before adding the destination through the admin interface using its `@username` or chat ID.

On the **接收目标** page, choose **默认设置** to edit a destination's default polling interval and message formatting. Each subscription can inherit or override these defaults.

### Global settings

The **全局配置** page controls the default and minimum polling intervals, subscription limits, and the message shown when a limit is reached. Changes take effect immediately. Deployment settings such as the bot token and proxies continue to be configured through environment variables.

## Per-destination OPML import and export

Each destination group has **Import OPML / Export OPML** buttons. You can also use the OPML button at the top of Subscriptions or next to a destination on the Destinations page, including destinations without subscriptions.

- Export downloads only the selected destination's subscriptions, including paused subscriptions, using the original bot's `/export` format. RSS URLs and custom titles are preserved.
- Import accepts `.opml` or XML files up to 2 MB and 1,000 feeds. Choose a destination and file, preview the count and existing subscriptions, then confirm. Preview does not fetch feeds or modify subscriptions.
- Import reuses the bot's subscription logic and respects destination subscription limits. Nested folders and duplicate URLs are handled by the original OPML parser.
- Like `/import`, importing an existing feed can update its custom title or reactivate that subscription. It does not remove subscriptions, and the other destinations' subscription settings remain unchanged.
- Results show successful and unsuccessful entries, including subscriptions already present or over the limit. Feed fetch failures do not undo successful imports.
- OPML carries URLs and titles, not keyword rules, message formatting, or pause state. Use ZIP backup/restore for those settings.

## Keyword filtering

Rules belong to each **subscription**. The same RSS feed can have different rules when delivered to different destinations.

| Interface label | Meaning |
| --- | --- |
| 必须包含 | Include keywords |
| 排除关键词 | Exclude keywords |
| 包含条件 | Match any or all include keywords |
| 匹配范围 | Search the title only, or the title and body |

- Enter one literal keyword per line. Regular expressions are not supported.
- Include rules can require any keyword or every keyword. An empty include list imposes no include restriction.
- A match for any exclude keyword blocks the article, even if the include rule matches.
- Matching removes HTML markup, normalizes full-width/half-width characters, and ignores letter case.
- Each include or exclude list allows up to 100 keywords, each up to 200 characters.
- Rules affect newly fetched articles. Filtered articles still enter the feed's delivery history; changing a rule does not resend older articles.
- Operational notifications, such as fetch errors or feed deactivation, bypass keyword filtering.

Startup automatically applies the new database field migration for SQLite or PostgreSQL. Back up the existing database before the first upgrade. Avoid rolling back the code directly after upgrading the database.

## ZIP backup and restore

A backup includes all destinations and their defaults, RSS feeds, article deduplication history, subscription formatting, keyword rules, and database global options.

You can optionally include runtime settings: bot token, managers, API credentials, Telegraph tokens, proxies, and supported network settings. Backups contain private chat information and may contain credentials; store them as sensitive files.

### Export

On **备份与还原**, optionally select **同时包含 … 运行配置** to include runtime settings, then choose **下载 ZIP 备份** to download the archive.

### Preview and merge restore

Upload a ZIP archive, review the validated record counts, and choose **确认合并还原** to confirm. Optionally select **还原备份中的运行配置** to restore runtime settings as well.

Restore matches destinations by chat ID, feeds by RSS URL, and subscriptions by their destination/feed pair. Internal database IDs are remapped, so they do not need to match between instances.

- Destination defaults, matching subscription settings, and global options from the backup overwrite their current values. Additional current subscriptions remain in place.
- Existing feeds keep their current fetch history. Newly created feeds inherit history from the backup to help avoid resending old articles.
- Database writes run in a transaction. A database import failure rolls back those writes.
- Before restoring, the current state is saved to `config/web-backups/<timestamp>.zip` with file permissions `0600`. You can upload that archive for a merge restore. This recovery backup does not automatically remove subscriptions added later.
- If runtime restoration is selected, settings are written to `config/web-restored.env` with permissions `0600`. **Restart the bot to apply them.** This file overrides matching values from the original `.env` and process environment. To return to the original deployment settings, move this file aside and restart.
- Restore does not overwrite `DATABASE_URL`, the web admin secret, or the web listen address/port. Telegram session files are not included.
- On a new machine, configure the bot token, managers, database connection, and web admin secret before starting the bot and importing a backup. The bot signs in to Telegram again.
- The upload and total uncompressed archive size are limited to 16 MB. Only this admin interface's v1 ZIP format is accepted. Uploaded archive paths are never extracted.

## Verification

Run from the repository root after installing the project's dependencies:

```console
PYTHONPATH=. python tests/test_admin.py
python tests/test_migrations.py
```

The tests use temporary SQLite databases and a local HTTP server without connecting to Telegram. They cover authentication, origin checks, subscription management, independent keyword rules, Unicode/HTML matching, backup previews, ID remapping, transaction rollback, runtime configuration restoration, and SQLite migrations.

Before production use, test private-chat, channel, and group permissions and actual delivery with your own bot. PostgreSQL migrations still need verification in a PostgreSQL environment.

## Source availability

This fork retains the upstream AGPLv3+ license. If you publish another fork, update `REPO_URL` in `src/i18n/__init__.py` to your public source repository so users can obtain the source for the version you run.
