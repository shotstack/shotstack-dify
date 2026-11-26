# Privacy

This plugin sends the data you give it to the Shotstack API at `api.shotstack.io`, and to no other host:

- Your Shotstack API key, as the `x-api-key` header.
- The edit JSON, the template ID and the merge fields you pass to a tool, and render IDs you look up.

The plugin itself collects no personal data. Anything personal you put in an edit or merge field (names, text, links
to images or video) is sent to Shotstack to render, and Shotstack hosts the rendered files at the URL it returns.

Shotstack processes that data to render your files and returns the result. The plugin does not store, log or forward
anything else. How Shotstack handles data is described in its privacy policy: https://shotstack.io/privacy
