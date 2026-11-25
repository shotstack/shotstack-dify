# Shotstack for Dify

Render video, image and audio from JSON or saved templates with the [Shotstack](https://shotstack.io) API, from a Dify
workflow, chatflow or agent.

## Set up

1. Copy your **Production** API key from the [Shotstack dashboard](https://shotstack.io/docs/guide/getting-started/request-api-keys/).
   Renders use credits from your Shotstack account.
2. In Dify, open the Shotstack plugin, click **Authorize** and paste the key.

## Tools

| Tool | What it does |
| --- | --- |
| **Render From JSON** | Renders a file from a Shotstack edit (a `timeline` and an `output`) and returns the URL. |
| **Render Template** | Renders a template saved in your account and fills its placeholders with merge fields. |
| **Get Render Status** | Checks a render by ID and returns its status and, when done, the URL. |
| **List Templates** | Lists your templates (ID, name, last updated), newest first. |

Both render tools can wait for the file (on by default, up to 300 seconds) or return the render ID straight away.
Each tool returns JSON, a text summary for agents, and one variable per field (`id`, `status`, `url`) for workflows.

## Example

A workflow with a Start node, a **Render From JSON** node and an End node that outputs `url`. Paste this into **Edit**:

```json
{"timeline":{"tracks":[{"clips":[{"asset":{"type":"title","text":"Hello from Dify","style":"minimal"},"start":0,"length":3}]}]},"output":{"format":"mp4","resolution":"sd"}}
```

In an agent, add the four tools and ask for a video. The edit format is in the
[Shotstack docs](https://shotstack.io/docs/guide/).

## Connection

The plugin makes HTTPS requests to `api.shotstack.io` and nothing else. It needs a Shotstack API key and no other setup.

## Notes

- Your key is only sent to `api.shotstack.io`. See [PRIVACY.md](PRIVACY.md).
- Generating AI images, video and audio is not in this version.
- Source and issues: https://github.com/shotstack/shotstack-dify
- Contributing and releases: [CONTRIBUTING.md](CONTRIBUTING.md). Changes: [CHANGELOG.md](CHANGELOG.md).
