// Main handler for HTML requests
async function handleRequest(request) {
  // Fetch the original HTML from yr.no
  const response = await fetch('https://www.yr.no/en/content/2-2654991/card.html');
  let html = await response.text();

  // Inject custom CSS to increase font size
  html = html.replace(
    '</head>',
    `
    <style>
      /* Increase base font size for the entire page */
      body {
        font-size: 28px !important;
      }
      .header {
        display: none;
      }
      .temperature {
        font-size: 32px !important;
      }
      /* Override inline styles (if needed) */
      * {
        font-size: inherit !important;
      }
      .current-hour__list-icon {
        width: 1.8rem;
        height: 1.8rem;
      }
      .table__body th {
        color: #000;
      }
      .current-hour__list-item {
        margin: 0 0 1rem 0;
      }
      .table__weather-symbol {
        width: 2.2rem;
        height: 2.2rem;
      }
    </style>
    </head>
    `
  );

  // Replace all absolute URLs with Worker-proxied URLs
  const workerHost = `https://${request.headers.get('host')}`;
  html = html.replace(
    /https:\/\/www\.yr\.no\/(assets\/.*?)/g,
    (match, assetPath) => `${workerHost}/proxy-asset?url=${encodeURIComponent(`https://www.yr.no/${assetPath}`)}`
  );

  // Return the modified HTML
  return new Response(html, {
    headers: { 'Content-Type': 'text/html' },
  });
}

// Handle proxied asset requests (e.g., images)
async function handleAssetRequest(request) {
  const url = new URL(request.url);
  const assetUrl = url.searchParams.get('url');

  if (!assetUrl) {
    return new Response('Invalid asset URL', { status: 400 });
  }

  // Fetch the asset (e.g., image) from yr.no
  const assetResponse = await fetch(assetUrl);

  if (!assetResponse.ok) {
    return new Response(`Failed to fetch asset: ${assetResponse.status}`, { status: 500 });
  }

  // Return the asset with the correct content type
  const contentType = assetResponse.headers.get('Content-Type');
  return new Response(await assetResponse.arrayBuffer(), {
    headers: {
      'Content-Type': contentType,
      'Cache-Control': 'public, max-age=3600',  // Cache assets for 1 hour
    },
  });
}

// Route requests to the appropriate handler
addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/proxy-asset')) {
    event.respondWith(handleAssetRequest(event.request));
  } else {
    event.respondWith(handleRequest(event.request));
  }
});
