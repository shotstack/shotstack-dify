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
Each tool returns JSON and a text summary for agents. The render and status tools also return one variable per field
(`id`, `status`, `url`) for workflows.

Renders with AI assets can take several minutes. For those, turn **Wait** off on the render step and add
**Get Render Status** after it with **Wait** on and Dify's **Retry on failure** enabled. Don't turn on retries for a
render step: each retry starts, and bills, a new render.

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
- AI images, video, voice and music work inside an edit: give an asset a `prompt` and a `model`, and Shotstack
  generates it during the render. A separate generate tool is not in this version.
- Source and issues: https://github.com/shotstack/shotstack-dify
- Contributing and releases: [CONTRIBUTING.md](https://github.com/shotstack/shotstack-dify/blob/main/CONTRIBUTING.md).
  Changes: [CHANGELOG.md](https://github.com/shotstack/shotstack-dify/blob/main/CHANGELOG.md).
