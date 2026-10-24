'use strict';
window.MenuAPI = {
  async request(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (options.method && !['GET','HEAD'].includes(options.method)) {
      headers.set('X-CSRF-Token', document.querySelector('meta[name="csrf-token"]').content);
      headers.set('Content-Type','application/json');
    }
    const response = await fetch(url, {...options,headers,cache:'no-store'});
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) throw new Error('Your login expired or was reset. Sign in again in another tab; your unpublished edits remain here.');
      throw new Error(data.error || 'Request failed.');
    }
    return data;
  },
  element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  },
  feedback(node, text, error = false) {node.textContent=text; node.classList.toggle('error',error);}
};
for(const link of document.querySelectorAll('.app-header nav a'))if(new URL(link.href).pathname===location.pathname)link.setAttribute('aria-current','page');
