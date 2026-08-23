import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { gsap } from "gsap";

const METRICS = ["composite", "quality", "growth", "balance_sheet", "valuation"];
const LABELS = {
  composite: "Composite",
  quality: "Quality",
  growth: "Growth",
  balance_sheet: "Balance sheet",
  valuation: "Valuation",
};
const COLORS = [0x0a7b66, 0x2878ff, 0x8a5cf6, 0xd97706];
const mountedInstances = new WeakMap();

function validCompanies(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.slice(0, 4).flatMap((company) => {
    if (!company || typeof company.symbol !== "string" || typeof company.name !== "string") {
      return [];
    }
    const values = {};
    for (const metric of METRICS) {
      const value = company.values?.[metric];
      values[metric] = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : null;
    }
    return [{ symbol: company.symbol.slice(0, 24), name: company.name.slice(0, 80), values }];
  });
}

function towerHeight(value) {
  return value === null ? 0.35 : 0.6 + (value / 100) * 5.2;
}

function disposeMaterial(material) {
  for (const value of Object.values(material)) {
    if (value && typeof value === "object" && typeof value.dispose === "function") {
      value.dispose();
    }
  }
  material.dispose();
}

export default function mountFinancialTowers(component) {
  const { data, parentElement } = component;
  const previousCleanup = mountedInstances.get(parentElement);
  if (previousCleanup) previousCleanup();

  const root = parentElement.querySelector("[data-testid='financial-towers']");
  const canvas = parentElement.querySelector("canvas");
  const stage = parentElement.querySelector(".tower-stage");
  const labelsLayer = parentElement.querySelector(".tower-labels");
  const detailName = parentElement.querySelector("[data-detail-name]");
  const detailValue = parentElement.querySelector("[data-detail-value]");
  const detailMetric = parentElement.querySelector("[data-detail-metric]");
  const fallback = parentElement.querySelector(".tower-fallback");
  const resetButton = parentElement.querySelector("[data-reset-view]");
  const metricButtons = [...parentElement.querySelectorAll("[data-metric]")];
  const companies = validCompanies(data?.companies);

  if (!root || !canvas || !stage || !labelsLayer || !detailName || !detailValue || !detailMetric) {
    return () => {};
  }

  if (companies.length < 2) {
    if (fallback) {
      fallback.hidden = false;
      fallback.textContent = "Add at least two companies to open the 3D comparison.";
    }
    return () => {};
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const duration = reduceMotion ? 0 : 0.72;
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch (_error) {
    canvas.hidden = true;
    if (fallback) {
      fallback.hidden = false;
      fallback.textContent = "3D view unavailable. Use the exact comparison chart and table above.";
    }
    return () => {};
  }

  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  const initialCamera = new THREE.Vector3(8.5, 6.8, 10.5);
  camera.position.copy(initialCamera);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.07;
  controls.minDistance = 6;
  controls.maxDistance = 22;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.target.set(0, 2.1, 0);

  scene.add(new THREE.HemisphereLight(0xffffff, 0xaeb8c5, 2.4));
  const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
  keyLight.position.set(6, 10, 8);
  scene.add(keyLight);
  const rimLight = new THREE.DirectionalLight(0x2878ff, 1.4);
  rimLight.position.set(-8, 5, -5);
  scene.add(rimLight);

  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(7.5, 64),
    new THREE.MeshBasicMaterial({ color: 0x8a94a3, transparent: true, opacity: 0.08 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.03;
  scene.add(floor);

  const towerGeometry = new THREE.BoxGeometry(1.55, 1, 1.55, 1, 12, 1);
  const towerRecords = [];
  const spacing = 2.45;
  const startX = -((companies.length - 1) * spacing) / 2;

  companies.forEach((company, index) => {
    const material = new THREE.MeshPhysicalMaterial({
      color: COLORS[index % COLORS.length],
      transparent: true,
      opacity: 0.68,
      roughness: 0.26,
      metalness: 0.08,
      transmission: 0.12,
      clearcoat: 0.85,
      clearcoatRoughness: 0.18,
    });
    const mesh = new THREE.Mesh(towerGeometry, material);
    const value = company.values.composite;
    const height = towerHeight(value);
    mesh.scale.y = height;
    mesh.position.set(startX + index * spacing, height / 2, 0);
    mesh.userData = { company, index };
    scene.add(mesh);

    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(towerGeometry),
      new THREE.LineBasicMaterial({ color: COLORS[index % COLORS.length], transparent: true, opacity: 0.7 })
    );
    edges.scale.y = height;
    edges.position.copy(mesh.position);
    scene.add(edges);

    const label = document.createElement("div");
    label.className = "tower-label";
    label.textContent = company.symbol;
    labelsLayer.append(label);
    towerRecords.push({ company, mesh, edges, label });
  });

  let activeMetric = "composite";
  let selectedIndex = 0;
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let frameId = 0;
  let visible = true;
  let disposed = false;

  function updateDetail(index) {
    const record = towerRecords[index];
    if (!record) return;
    const value = record.company.values[activeMetric];
    detailName.textContent = `${record.company.name} · ${record.company.symbol}`;
    detailMetric.textContent = LABELS[activeMetric];
    detailValue.textContent = value === null ? "Unavailable" : `${value.toFixed(0)} / 100`;
    selectedIndex = index;
  }

  function setMetric(metric) {
    if (!METRICS.includes(metric)) return;
    activeMetric = metric;
    metricButtons.forEach((button) => {
      const selected = button.dataset.metric === metric;
      button.setAttribute("aria-pressed", String(selected));
      button.classList.toggle("active", selected);
    });
    towerRecords.forEach((record) => {
      const height = towerHeight(record.company.values[metric]);
      gsap.to(record.mesh.scale, { y: height, duration, ease: "power3.inOut" });
      gsap.to(record.mesh.position, { y: height / 2, duration, ease: "power3.inOut" });
      gsap.to(record.edges.scale, { y: height, duration, ease: "power3.inOut" });
      gsap.to(record.edges.position, { y: height / 2, duration, ease: "power3.inOut" });
    });
    updateDetail(selectedIndex);
  }

  function resize() {
    const width = Math.max(stage.clientWidth, 280);
    const height = Math.max(stage.clientHeight, 360);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function updateLabels() {
    const width = stage.clientWidth;
    const height = stage.clientHeight;
    towerRecords.forEach((record) => {
      const point = record.mesh.position.clone();
      point.y += record.mesh.scale.y / 2 + 0.45;
      point.project(camera);
      record.label.style.transform = `translate(-50%, -50%) translate(${(point.x * 0.5 + 0.5) * width}px, ${(-point.y * 0.5 + 0.5) * height}px)`;
      record.label.hidden = point.z > 1;
    });
  }

  function renderFrame() {
    if (disposed || !visible) return;
    controls.update();
    updateLabels();
    renderer.render(scene, camera);
    frameId = requestAnimationFrame(renderFrame);
  }

  function pick(event) {
    const bounds = canvas.getBoundingClientRect();
    pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
    pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(towerRecords.map((record) => record.mesh))[0];
    canvas.style.cursor = hit ? "pointer" : "grab";
    if (hit) updateDetail(hit.object.userData.index);
  }

  function selectByKeyboard(event) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    if (event.key === "Home") selectedIndex = 0;
    else if (event.key === "End") selectedIndex = towerRecords.length - 1;
    else if (event.key === "ArrowLeft") selectedIndex = Math.max(0, selectedIndex - 1);
    else selectedIndex = Math.min(towerRecords.length - 1, selectedIndex + 1);
    updateDetail(selectedIndex);
  }

  function resetView() {
    gsap.to(camera.position, {
      x: initialCamera.x,
      y: initialCamera.y,
      z: initialCamera.z,
      duration,
      ease: "power3.out",
      onUpdate: () => controls.update(),
    });
    gsap.to(controls.target, { x: 0, y: 2.1, z: 0, duration, ease: "power3.out" });
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(stage);
  const intersectionObserver = new IntersectionObserver((entries) => {
    const nextVisible = entries.some((entry) => entry.isIntersecting);
    if (nextVisible && !visible) {
      visible = true;
      renderFrame();
    } else if (!nextVisible && visible) {
      visible = false;
      cancelAnimationFrame(frameId);
    }
  });
  intersectionObserver.observe(root);

  const metricHandlers = new Map();
  metricButtons.forEach((button) => {
    const handler = () => setMetric(button.dataset.metric);
    metricHandlers.set(button, handler);
    button.addEventListener("click", handler);
  });
  canvas.addEventListener("pointermove", pick);
  canvas.addEventListener("pointerdown", pick);
  canvas.addEventListener("keydown", selectByKeyboard);
  resetButton?.addEventListener("click", resetView);

  resize();
  updateDetail(0);
  setMetric("composite");
  renderFrame();

  const cleanup = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frameId);
    resizeObserver.disconnect();
    intersectionObserver.disconnect();
    controls.dispose();
    canvas.removeEventListener("pointermove", pick);
    canvas.removeEventListener("pointerdown", pick);
    canvas.removeEventListener("keydown", selectByKeyboard);
    resetButton?.removeEventListener("click", resetView);
    metricHandlers.forEach((handler, button) => {
      button.removeEventListener("click", handler);
    });
    towerRecords.forEach(({ mesh, edges, label }) => {
      gsap.killTweensOf(mesh.scale);
      gsap.killTweensOf(mesh.position);
      gsap.killTweensOf(edges.scale);
      gsap.killTweensOf(edges.position);
      label.remove();
    });
    gsap.killTweensOf(camera.position);
    gsap.killTweensOf(controls.target);
    scene.traverse((object) => {
      if (object.geometry) object.geometry.dispose();
      if (object.material) {
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach(disposeMaterial);
      }
    });
    renderer.dispose();
    renderer.forceContextLoss();
    mountedInstances.delete(parentElement);
  };

  mountedInstances.set(parentElement, cleanup);
  return cleanup;
}
