function getLocationAndSubmitForm(formId) {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            document.getElementById("latitude").value = position.coords.latitude;
            document.getElementById("longitude").value = position.coords.longitude;
            document.getElementById(formId).submit();
        }, function () {
            alert("Unable to get your location.");
        });
    } else {
        alert("Geolocation is not supported by your browser.");
    }
}
