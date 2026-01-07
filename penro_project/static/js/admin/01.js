document.addEventListener('DOMContentLoaded', function() {

  const cards = document.querySelectorAll('.wc-card');

  cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.zIndex = '10';
    });
    card.addEventListener('mouseleave', function() {
      this.style.zIndex = '1';
    });
  });

  cards.forEach(card => {
    card.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') {
        const link = this.querySelector('.wc-dropdown-item');
        if (link) {
          e.preventDefault();
          link.click();
        }
      }
    });
  });

  const editModal = document.getElementById('editWorkcycleModal');
  if (editModal) {
    editModal.addEventListener('show.bs.modal', function(event) {
      const btn = event.relatedTarget;
      this.querySelector('#edit_workcycle_id').value = btn.dataset.id;
      this.querySelector('#edit_title').value = btn.dataset.title;
      this.querySelector('#edit_description').value = btn.dataset.description;
      this.querySelector('#edit_due_at').value = btn.dataset.due;
    });
  }

  const reassignModal = document.getElementById('reassignWorkcycleModal');
  if (reassignModal) {
    reassignModal.addEventListener('show.bs.modal', function(event) {
      const btn = event.relatedTarget;
      this.querySelector('#reassign_workcycle_id').value = btn.dataset.id;
      this.querySelector('#reassign_workcycle_title').textContent = btn.dataset.title;
    });
  }
});

document.addEventListener("DOMContentLoaded", function () {
  const deleteModal = document.getElementById("deleteWorkcycleModal");
  if (!deleteModal) return;

  deleteModal.addEventListener("show.bs.modal", function (event) {
    deleteModal.querySelector("#deleteWorkcycleForm").action =
      event.relatedTarget.getAttribute("data-delete-url");
  });
});