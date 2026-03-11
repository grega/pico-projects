// Cloudflare Worker script to handle JSON payloads and store them in R2
// Requres an R2 bucket binding named `enviro_r2`
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  let payload;
  try {
    payload = await request.json();
  } catch (e) {
    return new Response('Invalid JSON payload', { status: 400 });
  }

  if (!payload.nickname || !payload.model || !payload.uid || !payload.timestamp || !payload.readings) {
    return new Response('Invalid payload structure', { status: 400 });
  }

  try {
    const dir = payload.nickname ? `${payload.nickname}-${payload.uid}` : payload.uid;
    const objectName = `${dir}/${payload.timestamp}.json`;
    await enviro_r2.put(objectName, JSON.stringify(payload));
    return new Response('Data stored successfully', { status: 200 });
  } catch (e) {
    return new Response('Failed to store data', { status: 500 });
  }
}
