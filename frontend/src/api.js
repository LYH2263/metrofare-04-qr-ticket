async function raiseFor(r) {
  if (r.ok) return
  let msg = await r.text()
  try {
    const body = JSON.parse(msg)
    if (body && typeof body.detail === 'string') msg = body.detail
  } catch (_) { /* keep raw text */ }
  throw new Error(msg)
}
export async function getJSON(path) {
  const r = await fetch(path)
  await raiseFor(r)
  return r.json()
}
export async function postJSON(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  await raiseFor(r)
  return r.json()
}
