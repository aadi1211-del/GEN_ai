(function () {
	"use strict";

	const $ = (selector, root = document) => root.querySelector(selector);

	function showToast(message, type = "info") {
		const toast = document.createElement("div");
		toast.className = `alert alert-${type} nf-toast shadow-sm mb-0`;
		toast.setAttribute("role", "status");
		toast.textContent = message;
		document.body.appendChild(toast);
		window.setTimeout(() => toast.remove(), 4200);
	}

	function setLoading(button, loading) {
		if (!button) return;
		button.classList.toggle("is-loading", loading);
		button.disabled = loading;
		if (loading) {
			button.dataset.originalText = button.innerHTML;
			button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Working...';
		} else if (button.dataset.originalText) {
			button.innerHTML = button.dataset.originalText;
			delete button.dataset.originalText;
		}
	}

	function autoGrow(textarea) {
		textarea.style.height = "auto";
		textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
	}

	document.addEventListener("DOMContentLoaded", () => {
		document.querySelectorAll("textarea").forEach((textarea) => {
			textarea.addEventListener("input", () => autoGrow(textarea));
			autoGrow(textarea);
		});

		document.querySelectorAll(".upload-zone").forEach((zone) => {
			["dragenter", "dragover"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
				event.preventDefault();
				zone.classList.add("is-dragover");
			}));
			["dragleave", "drop"].forEach((eventName) => zone.addEventListener(eventName, (event) => {
				event.preventDefault();
				zone.classList.remove("is-dragover");
			}));
			zone.addEventListener("drop", (event) => {
				const input = $("input[type=file]", zone);
				if (input && event.dataTransfer.files.length) {
					input.files = event.dataTransfer.files;
					input.dispatchEvent(new Event("change", { bubbles: true }));
				}
			});
		});

		document.querySelectorAll("form[data-api-form]").forEach((form) => {
			form.addEventListener("submit", async (event) => {
				event.preventDefault();
				const button = $("button[type=submit]", form);
				setLoading(button, true);
				try {
					const response = await fetch(form.action, {
						method: form.method || "POST",
						body: new FormData(form),
						headers: { Accept: "application/json" },
					});
					const data = await response.json();
					if (!response.ok) throw new Error(data.error || "The request could not be completed.");
					showToast(data.message || "Done.", "success");
					if (form.dataset.resetOnSuccess !== "false") form.reset();
					if (form.dataset.redirect) window.location.href = form.dataset.redirect;
				} catch (error) {
					showToast(error.message, "danger");
				} finally {
					setLoading(button, false);
				}
			});
		});

		document.querySelectorAll("[data-delete-url]").forEach((button) => {
			button.addEventListener("click", async () => {
				if (!window.confirm("Delete this document? This cannot be undone.")) return;
				setLoading(button, true);
				try {
					const response = await fetch(button.dataset.deleteUrl, {
						method: "DELETE",
						headers: { Accept: "application/json" },
					});
					if (!response.ok) throw new Error("Could not delete the document.");
					button.closest("[data-document-row]")?.remove();
					showToast("Document deleted.", "success");
				} catch (error) {
					showToast(error.message, "danger");
					setLoading(button, false);
				}
			});
		});

		const chatForm = $("#chat-form");
		if (chatForm) {
			chatForm.addEventListener("submit", async (event) => {
				event.preventDefault();
				const input = $("#chat-input");
				const messages = $("#chat-messages");
				const message = input.value.trim();
				if (!message) return;
				$("#chat-empty")?.remove();
				messages.insertAdjacentHTML("beforeend", `<div class="chat-message user mb-3"></div>`);
				messages.lastElementChild.textContent = message;
				input.value = "";
				const sendButton = $("button[type=submit]", chatForm);
				setLoading(sendButton, true);
				messages.insertAdjacentHTML("beforeend", '<div id="chat-thinking" class="chat-message assistant mb-3">Thinking...</div>');
				messages.scrollTop = messages.scrollHeight;
				const controller = new AbortController();
				const timeout = window.setTimeout(() => controller.abort(), 60000);
				try {
					const response = await fetch("/api/chat", {
						method: "POST",
						headers: { "Content-Type": "application/json", Accept: "application/json" },
						signal: controller.signal,
						body: JSON.stringify({
							message,
							session_id: chatForm.dataset.sessionId || null,
							document_id: $("#chat-document")?.value || null,
						}),
					});
					const responseText = await response.text();
					let data;
					try {
						data = JSON.parse(responseText);
					} catch {
						throw new Error(`Server returned an unexpected response (${response.status}).`);
					}
					if (!response.ok) throw new Error(data.error || "The message could not be sent.");
					chatForm.dataset.sessionId = data.session_id;
					$("#chat-thinking")?.remove();
					messages.insertAdjacentHTML("beforeend", `<div class="chat-message assistant mb-3"></div>`);
					messages.lastElementChild.innerHTML = data.reply_html || data.reply;
					messages.scrollTop = messages.scrollHeight;
				} catch (error) {
					$("#chat-thinking")?.remove();
					showToast(error.name === "AbortError" ? "The response took too long. Please try again." : error.message, "danger");
				} finally {
					window.clearTimeout(timeout);
					setLoading(sendButton, false);
				}
			});
		}
	});
})();
