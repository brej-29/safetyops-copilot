"use strict";
const examples = {
  fall: {
    text: "A worker slipped on a wet access platform and suffered a fracture. The area has been isolated for review.",
    severity: "medium",
    score: 55,
    reason:
      "Fracture mentioned. Review access, housekeeping and fall-prevention controls.",
  },
  electrical: {
    text: "An exposed electrical wire was found beside the loading area. No contact was reported; the site lead was notified.",
    severity: "low",
    score: 25,
    reason:
      "Electrical category, no harm keyword. A low heuristic score does not establish safety; a competent person must review the conditions.",
  },
  ppe: {
    text: "An operator was observed without a hardhat at the designated PPE entry point. The supervisor was notified.",
    severity: "low",
    score: 25,
    reason:
      "PPE observation identified. Verify suitable equipment and document the follow-up inspection.",
  },
};
for (const button of document.querySelectorAll("[data-example]"))
  button.addEventListener("click", () => {
    const e = examples[button.dataset.example];
    document.getElementById("example-text").value = e.text;
    for (const b of document.querySelectorAll("[data-example]"))
      b.setAttribute("aria-pressed", String(b === button));
    const target = document.getElementById("example-result");
    target.querySelector(".pill").className = "pill " + e.severity;
    target.querySelector(".pill").textContent =
      e.severity[0].toUpperCase() + e.severity.slice(1) + " severity";
    target
      .querySelector(".score")
      .replaceChildren(
        document.createTextNode(e.score),
        Object.assign(document.createElement("small"), {
          textContent: " / 100 priority",
        }),
      );
    target.querySelector(".explanation").textContent = e.reason;
    target.querySelector(".equation").textContent =
      e.score + " severity points + 0 recurrence points";
  });
if (
  !matchMedia("(prefers-reduced-motion: reduce)").matches &&
  "IntersectionObserver" in window
) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries)
        if (e.isIntersecting) {
          e.target.classList.add("in-view");
          observer.unobserve(e.target);
        }
    },
    { threshold: 0.25 },
  );
  document.querySelectorAll(".reveal").forEach((e) => observer.observe(e));
}
