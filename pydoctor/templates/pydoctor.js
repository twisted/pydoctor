function togglePrivate() {
    // Hide all private things by adding the private-hidden class to them.
    document.body.classList.toggle("private-hidden");
}

// On load, hide everything private
togglePrivate()
