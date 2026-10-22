const questionForm = document.getElementById("question-form");
const questionInput = document.getElementById("question");
const result = document.getElementById("result");
const emptyState = document.getElementById("empty-state");
const askButton = document.getElementById("ask-button");

function addText(parent, tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  parent.appendChild(element);
  return element;
}

function renderSources(sources) {
  if (!sources || !sources.length) return;
  addText(result, "h3", "Sources", "h6 fw-bold mt-4 mb-2");
  sources.forEach((source, index) => {
    const card = document.createElement("article");
    card.className = "source-card";
    const location = source.page ? ` · page ${source.page}` : "";
    addText(card, "div", `[${index + 1}] ${source.filename}${location}`, "source-title");
    addText(card, "p", source.text, "source-text");
    result.appendChild(card);
  });
}

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;

  emptyState.classList.add("d-none");
  result.replaceChildren();
  askButton.disabled = true;
  askButton.textContent = "Searching…";
  addText(result, "p", "Retrieving relevant passages and preparing an answer…", "text-secondary small");

  try {
    const csrfToken = questionForm.querySelector("[name=csrfmiddlewaretoken]").value;
    const response = await fetch("/ask/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
      body: JSON.stringify({ question }),
    });
    const data = await response.json();
    result.replaceChildren();
    if (!response.ok) {
      addText(result, "div", data.error || "The request could not be completed.", "alert alert-warning");
      renderSources(data.sources);
    } else {
      addText(result, "div", data.answer, "answer-box");
      renderSources(data.sources);
    }
  } catch (error) {
    result.replaceChildren();
    addText(result, "div", error.message, "alert alert-warning");
  } finally {
    askButton.disabled = false;
    askButton.textContent = "Ask";
  }
});
