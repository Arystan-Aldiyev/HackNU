export function initialize() {
    let fenway = { lat: 40.7484892471959, lng: -73.9855785714668 };
    const elevator = new google.maps.ElevationService();
    const infowindow = new google.maps.InfoWindow({});
    const geocoder = new google.maps.Geocoder();
    let map = new google.maps.Map(document.getElementById("map"), {
        center: fenway,
        zoom: 14,
    });
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const pos = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                };
                infowindow.setPosition(pos);
                infowindow.setContent("You are here!");
                infowindow.open(map);
                map.setCenter(pos);
                latInputField.value = pos.lat
                lngInputField.value = pos.lng
            },
            () => {
                handleLocationError(true, infowindow, map.getCenter());
            }
        );
    } else {
        // Browser doesn't support Geolocation
        handleLocationError(false, infowindow, map.getCenter());
    }
    // infowindow.open(map);
    // Add a listener for the click event. Display the elevation for the LatLng of
    // the click inside the infowindow.
    map.addListener("click", (event) => {
        panorama.setPosition({ lat: event.latLng.lat(), lng: event.latLng.lng() })
        if (panorama.getVisible()) {
            panorama.setPosition({ lat: event.latLng.lat(), lng: event.latLng.lng() })
        } else {
            document.getElementById("pano").style.color = "black"
            console.log("blabla")
        }; // If false, then 3D
        if (google.maps.StreetViewStatus) {
            panorama = new google.maps.StreetViewPanorama(
                document.getElementById("pano"),
                {
                    position: fenway,
                    pov: {
                        heading: 34,
                        pitch: 10,
                    },
                }
            );
        } else {
            console.log("Тут крч Доха ")
        }
        latInputField.value = event.latLng.lat();
        lngInputField.value = event.latLng.lng();
        // document.getElementById("switch").click()

        displayLocationElevation(event.latLng, elevator, infowindow);
    });
    let panorama = new google.maps.StreetViewPanorama(
        document.getElementById("pano"),
        {
            position: fenway,
            pov: {
                heading: 34,
                pitch: 20,
            },
        }
    );
    map.setStreetView(panorama);
    const showInfoButton = document.getElementById("showInfoButton")
    showInfoButton.addEventListener("click", () => myLocation(infowindow, map))

    // const switchButton = document.getElementById("switch");
    // switchButton.addEventListener("click", (event) => {
    //     let cur = event.target.firstChild.data
    //     if (cur == "Pano!") {
    //         document.getElementById("pano").style.display = "flex";
    //         document.getElementById("map").style.display = "none";
    //         switchButton.innerText = "Map!"
    //     } else {
    //         document.getElementById("pano").style.display = "none";
    //         document.getElementById("map").style.display = "flex";
    //         switchButton.innerText = "Pano!"
    //     }
    // })
    // const latForm = document.getElementById("lat")

    // const lngForm = document.getElementById("lng");

    // latForm.addEventListener("keypress", function (event) {
    //     if (event.key === "Enter") {
    //         lngForm.focus()
    //         // Cancel the default action, if needed
    //         event.preventDefault();
    //         // Trigger the button element with a click
    //     }
    // })
    // lngForm.addEventListener("keypress", function (event) {
    //     // If the user presses the "Enter" key on the keyboard
    //     if (event.key === "Enter") {
    //         // Cancel the default action, if needed
    //         panorama.setPosition({ lat: parseFloat(latForm.value), lng: parseFloat(lngForm.value) })
    //         event.preventDefault();
    //         // Trigger the button element with a click
    //         document.getElementById("switch").click();
    //     }
    // });
}

window.initialize = initialize;

export function onoff() {
    if (!document.getElementById("infoWindow").style.display || document.getElementById("infoWindow").style.display == 'none') {
        console.log("on")
        document.getElementById("infoWindow").style.display = "inline-block";
    } else {
        console.log("off")
        document.getElementById("infoWindow").style.display = "none";
    }
}

export function changeCoords(geocoder, map, infowindow) {
    console.log("shahhs")
    const pos = {
        lat: parseFloat(document.getElementById("latitude").value),
        lng: parseFloat(document.getElementById("longitude").value),
    }
    map.setCenter(pos)
    geocoder
        .geocode({ location: pos })
        .then((response) => {
            if (response.results[0]) {
                map.setZoom(14);

                const marker = new google.maps.Marker({
                    position: pos,
                    map: map,
                });

                infowindow.setContent(response.results[0].formatted_address);
                infowindow.open(map, marker);
            } else {
                window.alert("No results found");
            }
        })
        .catch((e) => window.alert("Geocoder failed due to: " + e));

}

export function displayLocationElevation(location, elevator, infowindow) {
    // Initiate the location request
    elevator
        .getElevationForLocations({
            locations: [location],
        })
        .then(({ results }) => {
            console.log("ну высота примерно " + results[0].elevation)
            infowindow.setPosition(location);
            // Retrieve the first result
            if (results[0]) {
                // Open the infowindow indicating the elevation at the clicked position.
                infowindow.setContent(
                    "Высота " +
                    results[0].elevation +
                    " метров щещен.\n" +
                    " А lat = " +
                    location.lat() +
                    " а lng = " +
                    location.lng()
                );
            } else {
                infowindow.setContent("No results found");
            }
        })
        .catch((e) =>
            infowindow.setContent("Elevation service failed due to: " + e)
        );
}

export function myLocation(infowindow, map) {
    console.log("jafjads")
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const pos = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                };
                infowindow.setPosition(pos);
                infowindow.setContent("You are here!");
                infowindow.open(map);
                map.setCenter(pos);
                latInputField.value = pos.lat
                lngInputField.value = pos.lng
            },
            () => {
                handleLocationError(true, infowindow, map.getCenter());
            }
        );
    } else {
        // Browser doesn't support Geolocation
        handleLocationError(false, infowindow, map.getCenter());
    }
}
// function handleDrop(e) {
//     e.stopPropagation(); e.preventDefault();
//     var f = e.dataTransfer.files[0];
//     /* f is a File */
//     var reader = new FileReader();
//     reader.onload = function (e) {
//         var data = e.target.result;
//         /* reader.readAsArrayBuffer(file) -> data will be an ArrayBuffer */
//         var workbook = XLSX.read(data);
//         console.log(workbook)
//         /* DO SOMETHING WITH workbook HERE */
//     };
//     reader.readAsArrayBuffer(f);
// }
