// Adds a one-time spin animation to cards on page load and
// provides an optional trigger for spinning via buttons.

document.addEventListener('DOMContentLoaded', () => {
  // Automatically spin any card-like elements when the page loads.
  document.querySelectorAll('.card, .fighter-card').forEach((card) => {
    triggerSpin(card);
  });

  // Attach click handlers for elements that declare a spin target.
  document.querySelectorAll('[data-spin-target]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const selector = btn.getAttribute('data-spin-target');
      document.querySelectorAll(selector).forEach((el) => {
        triggerSpin(el);
      });
    });
  });
});

// Apply the spin-once class and remove it when the animation ends so
// it can be reapplied later.
function triggerSpin(el) {
  el.classList.remove('spin-once');
  // Force a reflow to allow restarting the animation if the class was present.
  void el.offsetWidth; // eslint-disable-line no-unused-expressions
  el.classList.add('spin-once');
  el.addEventListener(
    'animationend',
    () => el.classList.remove('spin-once'),
    { once: true }
  );
}
