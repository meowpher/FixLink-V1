// specific syntax for Motion One
import { animate, stagger, inView } from "https://cdn.skypack.dev/motion";

document.addEventListener("DOMContentLoaded", () => {
    // Animate main content on load
    animate(
        ".main-content",
        { opacity: [0, 1], y: [20, 0] },
        { duration: 0.8, easing: "ease-out" }
    );

    // Stagger animate cards
    inView(".card", (info) => {
        animate(
            info.target,
            { opacity: [0, 1], y: [30, 0] },
            { duration: 0.6, easing: "ease-out" }
        );
    });

    // Animate buttons on hover
    const buttons = document.querySelectorAll(".btn");
    buttons.forEach((btn) => {
        btn.addEventListener("mouseenter", () => {
            animate(btn, { scale: 1.05 }, { duration: 0.2 });
        });
        btn.addEventListener("mouseleave", () => {
            animate(btn, { scale: 1 }, { duration: 0.2 });
        });
    });

    // Navbar entrance
    animate(
        ".navbar",
        { opacity: [0, 1], y: [-20, 0] },
        { duration: 0.6, delay: 0.2 }
    );
});
