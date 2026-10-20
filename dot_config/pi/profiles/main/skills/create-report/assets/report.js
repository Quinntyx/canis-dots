(() => {
  const content = document.createElement('main');
  content.id = 'report-content';
  while (document.body.firstChild) content.append(document.body.firstChild);
  document.body.append(content);

  let scale = '1.5';
  const images = [];
  const buttons = [];
  const toolbar = document.createElement('nav');
  toolbar.className = 'report-toolbar';
  toolbar.setAttribute('aria-label', 'Report viewing controls');
  const controls = document.createElement('div');
  controls.className = 'scale-controls';
  const label = document.createElement('span');
  label.textContent = 'Screenshots';
  controls.append(label);

  function resizeImage(image) {
    const value = image.closest('details') ? 'fit' : scale;
    image.style.width = value === 'fit' ? '100%' :
      Math.round(image.naturalWidth * Number(value)) + 'px';
  }

  function setScale(value) {
    scale = value;
    for (const image of images) resizeImage(image);
    for (const button of buttons) {
      button.setAttribute('aria-pressed', String(button.dataset.scale === value));
    }
  }

  for (const [value, text] of [
    ['fit', 'Fit width'], ['1', '100%'], ['1.5', '150%'], ['2', '200%']
  ]) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.scale = value;
    button.textContent = text;
    button.setAttribute('aria-pressed', String(value === scale));
    button.addEventListener('click', () => setScale(value));
    buttons.push(button);
    controls.append(button);
  }
  toolbar.append(controls);

  const help = document.createElement('p');
  help.className = 'toolbar-help';
  help.textContent = '150% by default · scroll images sideways · originals open separately';
  toolbar.append(help);

  const select = document.createElement('select');
  select.className = 'section-select';
  select.setAttribute('aria-label', 'Jump to report section');
  const placeholder = document.createElement('option');
  placeholder.textContent = 'Jump to a section…';
  placeholder.value = '';
  select.append(placeholder);
  for (const heading of content.querySelectorAll('h2')) {
    const option = document.createElement('option');
    option.value = heading.id;
    option.textContent = heading.textContent;
    select.append(option);
  }
  select.addEventListener('change', () => {
    if (select.value) document.getElementById(select.value)?.scrollIntoView();
  });
  if (select.options.length > 1) toolbar.append(select);
  document.body.prepend(toolbar);

  function takeDescription(original, kind) {
    const next = original.nextElementSibling;
    if (next?.matches('p') && new RegExp('^' + kind + '\\s+\\d+\\b', 'i')
      .test(next.textContent.trim())) {
      next.classList.add('authored-caption');
      return next;
    }
    return original.querySelector('figcaption');
  }

  let figureNumber = 0;
  for (const image of [...content.querySelectorAll('img')]) {
    figureNumber++;
    const original = image.closest('figure') || image.parentElement;
    const description = takeDescription(original, 'Figure');
    const figure = document.createElement('figure');
    figure.className = 'screenshot-figure';
    const heading = document.createElement('div');
    heading.className = 'figure-heading';
    const title = document.createElement('span');
    title.textContent = 'Figure ' + figureNumber;
    const link = document.createElement('a');
    link.href = image.getAttribute('src');
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = 'Open original ↗';
    link.setAttribute('aria-label', 'Open original: ' + (image.alt || title.textContent));
    heading.append(title, link);
    const viewport = document.createElement('div');
    viewport.className = 'image-viewport';
    viewport.tabIndex = 0;
    viewport.setAttribute('role', 'region');
    viewport.setAttribute('aria-label', (image.alt || title.textContent) + '; scroll sideways');
    const caption = document.createElement('figcaption');
    if (description) {
      while (description.firstChild) caption.append(description.firstChild);
      description.remove();
    } else {
      caption.textContent = 'Figure ' + figureNumber + ' — ' +
        (image.alt || 'Image without an authored description.');
    }
    figure.append(heading, viewport, caption);
    original.replaceWith(figure);
    viewport.append(image);
    const compact = /contact[ -]?sheet|contact sheet/i.test(image.alt + ' ' + image.src);
    if (compact) {
      const details = document.createElement('details');
      details.className = 'compact-contact';
      const summary = document.createElement('summary');
      summary.textContent = 'Compact contact sheet (optional overview)';
      details.append(summary);
      figure.replaceWith(details);
      details.append(figure);
    }
    images.push(image);
    image.addEventListener('load', () => resizeImage(image));
    if (image.complete && image.naturalWidth) resizeImage(image);
  }

  let tableNumber = 0;
  for (const table of [...content.querySelectorAll('table')]) {
    tableNumber++;
    const description = takeDescription(table, 'Table');
    const caption = table.querySelector(':scope > caption');
    const wrapper = document.createElement('figure');
    wrapper.className = 'table-figure';
    const viewport = document.createElement('div');
    viewport.className = 'table-viewport';
    viewport.tabIndex = 0;
    viewport.setAttribute('role', 'region');
    viewport.setAttribute('aria-label', 'Table ' + tableNumber + '; scroll if needed');
    const footer = document.createElement('figcaption');
    footer.id = 'report-table-caption-' + tableNumber;
    if (description || caption) {
      const source = description || caption;
      while (source.firstChild) footer.append(source.firstChild);
      source.remove();
    } else {
      const headers = [...table.querySelectorAll('thead th')].map(h => h.textContent.trim());
      footer.textContent = 'Table ' + tableNumber + ' — Columns: ' + headers.join('; ') + '.';
      footer.dataset.inferred = 'true';
    }
    table.setAttribute('aria-describedby', footer.id);
    table.replaceWith(wrapper);
    viewport.append(table);
    wrapper.append(viewport, footer);
  }
})();
