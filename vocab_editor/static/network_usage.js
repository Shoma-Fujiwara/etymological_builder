(() => {
    const params = new URLSearchParams(location.search);

    // テスト内のネットワークは計測しない
    if (params.get("mode") === "quiz") return;

    const sessionId = crypto.randomUUID();

    let visibleSeconds = 0;
    let activeSeconds = 0;
    let openCount = 1;

    let lastTick = performance.now();
    let lastActivity = -Infinity;
    let isVisible = !document.hidden;

    function tick() {
        const now = performance.now();

        if (isVisible) {
            visibleSeconds += (now - lastTick) / 1000;

            activeSeconds += Math.max(
                0,
                Math.min(now, lastActivity + 60000) - lastTick
            ) / 1000;
        }

        lastTick = now;
    }

    function markActivity() {
        tick();
        lastActivity = performance.now();
    }

    ["pointerdown", "keydown", "wheel", "change"].forEach(name => {
        document.addEventListener(name, markActivity);
    });

    document.addEventListener("visibilitychange", () => {
        tick();
        isVisible = !document.hidden;
    });

    setInterval(tick, 1000);

    function sendUsage() {
        tick();

        if (visibleSeconds <= 0 && openCount === 0) return;

        const payload = {
            session_id: sessionId,
            event_id: crypto.randomUUID(),
            visible_seconds: visibleSeconds,
            active_seconds: activeSeconds,
            open_count: openCount
        };

        visibleSeconds = 0;
        activeSeconds = 0;
        openCount = 0;

        fetch("/api/network/log", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload),
            keepalive: true
        })
        .then(response => {
            if (!response.ok) throw new Error("保存失敗");
        })
        .catch(error => {
            console.error("ネットワークログ保存エラー:", error);
        });
    }

    setInterval(sendUsage, 30000);
    window.addEventListener("pagehide", sendUsage);
})();