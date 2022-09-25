import {
  AmbientLight,
  DirectionalLight,
  Matrix4,
  PerspectiveCamera,
  Scene,
  WebGLRenderer,
} from "three";

import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader";

import * as mapVisualizer from './index.js'
let marker1: google.maps.Marker;
let geodesicPoly: google.maps.Polyline;

let map: google.maps.Map;

let mapOptions = {
  zoom: 18,
  heading: 180,
  tilt: 45,
  center: {
    lat: 40.714,
    lng: -74.006,
  },
  mapId: "15431d2b469f209e",
};

function initMap(): void {
  mapVisualizer.initialize()
  const knopka = document.getElementById("knopka")
  knopka.addEventListener("click", turnOn3D)
}

function turnOn3D() {
  console.log(11)

  document.body.innerHTML = `
  <div id="floating-panel">
      <input id="latlng" type="text" value="40.714224,-73.961452" />
      <input id="submit" type="button" value="Reverse Geocode" />
      <button id="hehe">Click</button>
      <button id="animation">Animation</button>

    </div>
    <div id="map"></div>
  `;
  main3d()
}
function main3d() {
  const elevator = new google.maps.ElevationService();
  const geocoder = new google.maps.Geocoder();
  const infowindow = new google.maps.InfoWindow();

  const map = new google.maps.Map(
    document.getElementById("map") as HTMLElement,
    mapOptions
  );

  const buttons: [string, string, number, google.maps.ControlPosition][] = [
    ["Rotate Left", "rotate", 20, google.maps.ControlPosition.LEFT_CENTER],
    ["Rotate Right", "rotate", -20, google.maps.ControlPosition.RIGHT_CENTER],
    ["Tilt Down", "tilt", 20, google.maps.ControlPosition.TOP_CENTER],
    ["Tilt Up", "tilt", -20, google.maps.ControlPosition.BOTTOM_CENTER],
  ];

  (document.getElementById("submit") as HTMLElement).addEventListener(
    "click",
    () => {
      geocodeLatLng(geocoder, map, infowindow);
    }
  );

  marker1 = new google.maps.Marker({
    map,
    draggable: true,
    position: { lat: 40.714, lng: -74.006 },
  });

  geodesicPoly = new google.maps.Polyline({
    strokeColor: "#CC0099",
    strokeOpacity: 1.0,
    strokeWeight: 3,
    geodesic: true,
    map: map,
  });

  let path = [
    marker1.getPosition() as google.maps.LatLng,
  ];
  geodesicPoly.setPath(path);

  buttons.forEach(([text, mode, amount, position]) => {
    const controlDiv = document.createElement("div");
    const controlUI = document.createElement("button");

    controlUI.classList.add("ui-button");
    controlUI.innerText = `${text}`;
    controlUI.addEventListener("click", () => {
      adjustMap(mode, amount);
    });
    controlDiv.appendChild(controlUI);
    map.controls[position].push(controlDiv);
  });

  const adjustMap = function (mode: string, amount: number) {
    switch (mode) {
      case "tilt":
        map.setTilt(map.getTilt()! + amount);
        break;
      case "rotate":
        map.setHeading(map.getHeading()! + amount);
        break;
      default:
        break;
    }
  };
  map.addListener("click", (event) => {
    displayLocationElevation(event.latLng, elevator, infowindow, map);
  });

  (document.getElementById("animation") as HTMLElement).addEventListener(
    "click",
    () => {
      return initWebglOverlayView(map);
    }
  );
}
function geocodeLatLng(
  geocoder: google.maps.Geocoder,
  map: google.maps.Map,
  infowindow: google.maps.InfoWindow
) {
  const input = (document.getElementById("latlng") as HTMLInputElement).value;
  const latlngStr = input.split(",", 2);
  const latlng = {
    lat: parseFloat(latlngStr[0]),
    lng: parseFloat(latlngStr[1]),
  };
  geocoder
    .geocode({ location: latlng })
    .then((response) => {
      if (response.results[0]) {
        map.setZoom(18);
        map.setCenter(latlng);
        map.setTilt(45);
        mapOptions.zoom = 18;
        mapOptions.center = latlng;
        mapOptions.tilt = 45
        let marker = new google.maps.Marker({
          map,
          draggable: true,
          position: latlng,
        });
        const path = geodesicPoly.getPath();
        path.push(marker.getPosition() as google.maps.LatLng);
        infowindow.setContent(response.results[0].formatted_address);
        infowindow.open(map, marker);
      } else {
        window.alert("No results found");
      }
    })
    .catch((e) => window.alert("Geocoder failed due to: " + e));
}


function initWebglOverlayView(map: google.maps.Map): void {
  let scene, renderer, camera, loader;
  const webglOverlayView = new google.maps.WebGLOverlayView();

  webglOverlayView.onAdd = () => {
    // Set up the scene.

    scene = new Scene();

    camera = new PerspectiveCamera();

    const ambientLight = new AmbientLight(0xffffff, 0.75); // Soft white light.
    scene.add(ambientLight);

    const directionalLight = new DirectionalLight(0xffffff, 0.25);
    directionalLight.position.set(0.5, -1, 0.5);
    scene.add(directionalLight);

    // Load the model.
    loader = new GLTFLoader();
    const source =
      "https://raw.githubusercontent.com/googlemaps/js-samples/main/assets/pin.gltf";
    loader.load(source, (gltf) => {
      gltf.scene.scale.set(10, 10, 10);
      gltf.scene.rotation.x = Math.PI; // Rotations are in radians.
      scene.add(gltf.scene);
    });
  };

  webglOverlayView.onContextRestored = ({ gl }) => {
    // Create the js renderer, using the
    // maps's WebGL rendering context.
    renderer = new WebGLRenderer({
      canvas: gl.canvas,
      context: gl,
      ...gl.getContextAttributes(),
    });
    renderer.autoClear = false;

    // Wait to move the camera until the 3D model loads.
    loader.manager.onLoad = () => {
      renderer.setAnimationLoop(() => {
        webglOverlayView.requestRedraw();
        const { tilt, heading, zoom } = mapOptions;
        map.moveCamera({ tilt, heading, zoom });

        // Rotate the map 360 degrees.
        if (mapOptions.tilt < 67.5) {
          mapOptions.tilt += 0.5;
        } else if (mapOptions.heading <= 360) {
          mapOptions.heading += 0.2;
          mapOptions.zoom -= 0.0005;
        } else {
          renderer.setAnimationLoop(null);
        }
      });
    };
  };

  webglOverlayView.onDraw = ({ gl, transformer }): void => {
    const latLngAltitudeLiteral: google.maps.LatLngAltitudeLiteral = {
      lat: mapOptions.center.lat,
      lng: mapOptions.center.lng,
      altitude: 100,
    };

    // Update camera matrix to ensure the model is georeferenced correctly on the map.
    const matrix = transformer.fromLatLngAltitude(latLngAltitudeLiteral);
    camera.projectionMatrix = new Matrix4().fromArray(matrix);

    webglOverlayView.requestRedraw();
    renderer.render(scene, camera);

    // Sometimes it is necessary to reset the GL state.
    renderer.resetState();
  };
  webglOverlayView.setMap(map);
}


function displayLocationElevation(location, elevator, infowindow, map: google.maps.Map,) {
  elevator
    .getElevationForLocations({
      locations: [location],
    })
    .then(({ results }) => {
      infowindow.setPosition(location);

      if (typeof (results[0].elevation) !== "undefined") {
        map.setZoom(18);
        map.setCenter(location);
        map.setTilt(45);
        mapOptions.zoom = 18;
        mapOptions.center = location;
        mapOptions.tilt = 45;
        infowindow.setContent(
          "The elevation at this point <br>is " +
          results[0].elevation.toFixed(2) +
          "meters. Lat: " + location.lat() + "Lng: " + location.lng()
        );
        document.getElementById("latlng").value = location.lat() + ", " + location.lng()
      } else {
        infowindow.setContent("No results found");
      }
    })
    .catch((e) =>
      infowindow.setContent("Elevation service failed due to: " + e)
    );
}

window.initMap = initMap;
