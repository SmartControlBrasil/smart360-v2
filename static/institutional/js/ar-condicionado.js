/* A native, keyboard-accessible popup; YouTube is loaded only after a click. */
(() => {
  const dialog = document.getElementById('ac-video-dialog');
  const trigger = document.querySelector('[data-ac-video]');
  if (!dialog || !trigger) return;

  trigger.addEventListener('click', () => {
    const frame = dialog.querySelector('.ac-video-frame');
    if (frame && !frame.firstChild && dialog.dataset.embedUrl) {
      const iframe = document.createElement('iframe');
      iframe.src = dialog.dataset.embedUrl;
      iframe.title = 'Vídeo de Ar-Condicionado';
      iframe.allow = 'autoplay; encrypted-media; picture-in-picture';
      iframe.allowFullscreen = true;
      frame.appendChild(iframe);
    }
    dialog.showModal();
  });

  dialog.querySelector('[data-close-video]').addEventListener('click', () => dialog.close());

  dialog.addEventListener('click', (event) => {
    const rect = dialog.getBoundingClientRect();
    if (
      event.target === dialog
      && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)
    ) {
      dialog.close();
    }
  });

  dialog.addEventListener('close', () => {
    dialog.querySelector('.ac-video-frame')?.replaceChildren();
    trigger.focus();
  });
})();
