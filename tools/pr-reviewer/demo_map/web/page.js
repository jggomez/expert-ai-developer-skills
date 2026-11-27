// Clients to Review page: fetches the list and renders it.
export async function renderClients(root, owner) {
  const response = await fetch(`/clients/to-review?owner=${owner}`);
  const clients = await response.json();
  root.innerHTML = clients.map((c) => `<li>${c.name}</li>`).join("");
}
