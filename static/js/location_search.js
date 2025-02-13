function initAutocomplete() {
    document.querySelectorAll('[id$="location"]').forEach(function (input) {
        if (!input.classList.contains('autocomplete-initialized')) {
            input.classList.add('autocomplete-initialized');
            var autocomplete = new google.maps.places.Autocomplete(input);
            autocomplete.setFields(['formatted_address']);
            autocomplete.addListener('place_changed', function () {
                var place = autocomplete.getPlace();
                if (place.formatted_address) {
                    input.value = place.formatted_address;
                }
            });
        }
    });
}

document.addEventListener('DOMContentLoaded', initAutocomplete);
