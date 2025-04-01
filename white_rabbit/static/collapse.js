// JavaScript to handle collapse functionality
document.addEventListener('DOMContentLoaded', function () {
  // Find all collapse elements
  const collapseElements = document.querySelectorAll('.collapse');

  collapseElements.forEach(function (collapse) {
    // Find the title element within this collapse
    const title = collapse.querySelector('.collapse-title');

    if (title) {
      // Add click event listener to the title
      title.addEventListener('click', function () {
        // Toggle the 'open' attribute on the collapse element
        if (collapse.hasAttribute('open')) {
          collapse.removeAttribute('open');
        } else {
          collapse.setAttribute('open', '');
        }
      });
    }

    // Initialize with tabindex for accessibility
    if (!collapse.hasAttribute('tabindex')) {
      collapse.setAttribute('tabindex', '0');
    }

    // Add keyboard support (Enter and Space keys)
    collapse.addEventListener('keydown', function (event) {
      // In a keydown event, event.key is available
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (collapse.hasAttribute('open')) {
          collapse.removeAttribute('open');
        } else {
          collapse.setAttribute('open', '');
        }
      }
    });
  });
});