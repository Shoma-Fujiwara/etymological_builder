function setupNetwork(question, isCorrect) {
    const area = document.getElementById("networkArea");
    const frame = document.getElementById("networkFrame");
    const toggle = document.getElementById("networkToggle");

    const params = new URLSearchParams({
        mode: "quiz",
        chapter: question.chapter,
        stack: question.stack,
        word: question.word
    });

    area.hidden = false;

    function openNetwork() {
        if (!frame.getAttribute("src")) {
            frame.src = `/network?${params.toString()}`;
        }

        frame.hidden = false;
        toggle.textContent = "語源ネットワークを閉じる";
    }

    function closeNetwork() {
        frame.hidden = true;
        toggle.textContent = "語源ネットワークを表示";
    }

    toggle.onclick = () => {
        if (frame.hidden) {
            openNetwork();
        } else {
            closeNetwork();
        }
    };

    if (isCorrect) {
        closeNetwork();
    } else {
        openNetwork();
    }
}