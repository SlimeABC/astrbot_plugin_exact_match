# Exact Match

An AstrBot auto-reply plugin that responds only when a message exactly matches a configured trigger, avoiding substring false triggers.

## Features

- **Exact match** – With the trigger `test`, only `test` matches; `Test` and `test123` do not
- **Group-based rules** – Each rule pairs a trigger with a reply; add as many independent rules as you need
- **Configurable group trigger** – Each rule can require a mention (or the wake prefix) in group chats; disable it to reply to plain group messages. Private chats always match directly
- **Direct reply** – No model call, so replies are stable and cost nothing extra

## Installation

1. Put the plugin directory under `AstrBot/data/plugins/`
2. In the WebUI, go to Plugins → Reload Plugins
3. Open the plugin configuration and add rules under “Exact match rules”

## Configuration

“Exact match rules” is a list of groups. Each group contains:

| Field | Description |
| --- | --- |
| Trigger | Message text that must match exactly, without the wake prefix. Leading and trailing spaces are ignored; matching is case-sensitive |
| Bot (ID) | Enter the Bot ID shown in the platform settings. The bot account ID also works. Leave empty to apply to all bots |
| Require bot trigger | Enabled by default. When enabled, this rule needs a mention or the wake prefix in group chats; when disabled, a plain group message also triggers it. Private chats are unaffected |
| Reply | Text sent directly on a match; line breaks are supported |

Default rule:

- `test` → `pass`

If the same trigger is configured more than once, the first rule whose Bot ID and trigger requirements match is used.

> Since 1.0.1 the configuration is group-based. After upgrading from 1.0.0, the old trigger-list / reply-list settings are no longer used; please add the rules again in the WebUI.

## Usage example

Configuration:

- `test` → `pass`
- `help` → `help document` line break `v1.0` line break `this is a bot`

Conversation (private chat example; in group chats, mention the bot or use the wake prefix first):

```text
User: test
Bot: pass

User: help
Bot: help document
     v1.0
     this is a bot

User: Test
Bot: (Falls back to the LLM or no response)

User: help me!!!
Bot: (Falls back to the LLM or no response)
```

## Notes

- Matching is case-sensitive; `Test` does not trigger `test`
- Private chats always match directly; each rule can require a bot trigger, so group chats need a mention (or the wake prefix) by default
- If a rule specifies a Bot (ID), only that bot replies; leave it empty to apply the rule to all bots
- Matching uses the text with the wake prefix and bot mentions removed
- Rules with an empty trigger or empty reply are skipped
