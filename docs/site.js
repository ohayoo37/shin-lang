'use strict';
document.getElementById('copy').addEventListener('click', async (event) => {
  const button = event.currentTarget;
  const status = document.getElementById('copy-status');
  try {
    await navigator.clipboard.writeText(document.getElementById('commands').textContent);
    status.textContent = button.dataset.success;
  } catch {
    status.textContent = button.dataset.failure;
  }
});
