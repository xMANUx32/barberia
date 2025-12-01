function toggleChat() {
    const chatbox = document.getElementById("chatbox");
    if (chatbox.style.display === "none" || chatbox.style.display === "") {
        chatbox.style.display = "block";
        scrollChatToBottom();
    } else {
        chatbox.style.display = "none";
    }
}

function scrollChatToBottom() {
    const content = document.getElementById("chat-content");
    content.scrollTop = content.scrollHeight;
}

function mostrarMensajeBot(texto) {
    const content = document.getElementById("chat-content");
    const botMsg = document.createElement("div");
    botMsg.classList.add("msg", "bot");
    botMsg.innerHTML = texto.replace(/\n/g, '<br>');
    content.appendChild(botMsg);
    scrollChatToBottom();
}

function mostrarMensajeUsuario(texto) {
    const content = document.getElementById("chat-content");
    const userMsg = document.createElement("div");
    userMsg.classList.add("msg", "user");
    userMsg.textContent = texto;
    content.appendChild(userMsg);
    scrollChatToBottom();
}

function mostrarBotonesBarberos(barberos) {
    const content = document.getElementById("chat-content");
    const container = document.createElement("div");
    container.classList.add("botones-barberos");

    barberos.forEach(barbero => {
        const btn = document.createElement("button");
        btn.textContent = barbero.nombre;
        btn.classList.add("btn-barbero");
        btn.onclick = () => {
            enviarPreguntaBarbero(barbero.id, barbero.nombre);
            // Eliminar los botones después de seleccionar para evitar doble click
            container.remove();
        };
        container.appendChild(btn);
    });

    content.appendChild(container);
    scrollChatToBottom();
}

function enviarPregunta(pregunta) {
    if (!pregunta.trim()) return;

    mostrarMensajeUsuario(pregunta);

    fetch('/api/chatbox/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ pregunta: pregunta })
    })
    .then(res => res.json())
    .then(data => {
        if (data.barberos) {
            mostrarMensajeBot("Selecciona un barbero para ver su disponibilidad:");
            mostrarBotonesBarberos(data.barberos);
        } else {
            mostrarMensajeBot(data.respuesta);
        }
    })
    .catch(err => {
        mostrarMensajeBot("Lo siento, hubo un error en la respuesta.");
        console.error(err);
    });
}

function enviarPreguntaBarbero(barberoId, barberoNombre) {
    mostrarMensajeUsuario(`Mostrar disponibilidad de ${barberoNombre}`);

    fetch('/api/chatbox/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ pregunta: `disponibilidad barbero ${barberoId}` })
    })
    .then(res => res.json())
    .then(data => {
        mostrarMensajeBot(data.respuesta);
    })
    .catch(err => {
        mostrarMensajeBot("Lo siento, hubo un error en la respuesta.");
        console.error(err);
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let c of cookies) {
            const cookie = c.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}