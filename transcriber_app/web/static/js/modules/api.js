/**
 * Módulo de API y comunicación con el servidor
 * Gestiona todas las peticiones fetch al backend
 */

import { hideOverlay, setStatusText, showOverlay } from "./ui.js";
import { normalizeText } from "./utils.js";

/**
 * Procesa una transcripción existente con un nuevo modo
 */
async function processExistingTranscription(nombre, modo, transcription = null) {
    const formData = new FormData();
    formData.append("nombre", nombre);
    formData.append("modo", modo);

    if (transcription) {
        formData.append("transcription", transcription);
    }

    showOverlay();

    try {
        const response = await fetch("/api/process-existing", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.status === "done") {
            // Si el backend no devuelve el contenido directamente, lo buscamos
            let mdContent = data.content || data.markdown || data.resultado || "";

            if (!mdContent) {
                console.log("Contenido no recibido en respuesta directa. Fetching explícito...");
                const fetchedMd = await loadMarkdownResult(nombre, modo);
                if (fetchedMd) mdContent = fetchedMd;
            }

            return {
                success: true,
                mode: data.mode || modo,
                content: mdContent
            };
        } else {
            return {
                success: false,
                error: "Error procesando la transcripción existente."
            };
        }
    } catch (err) {
        console.error("Error:", err);
        return {
            success: false,
            error: "Error procesando la transcripción existente."
        };
    } finally {
        hideOverlay();
    }
}

/**
 * Envía un chunk del archivo de audio al servidor
 */
async function uploadChunk(chunk, chunkIndex, totalChunks, uploadId, nombre, modo, email, extension) {
    console.log(`[CHUNK UPLOAD] Enviando chunk ${chunkIndex + 1}/${totalChunks} (${(chunk.size / 1024 / 1024).toFixed(2)} MB)`);

    const formData = new FormData();
    formData.append("chunk", chunk);
    formData.append("chunkIndex", chunkIndex);
    formData.append("totalChunks", totalChunks);
    formData.append("uploadId", uploadId);
    formData.append("nombre", nombre);
    formData.append("modo", modo);
    formData.append("email", email);
    formData.append("extension", extension);

    try {
        const response = await fetch("/api/upload-chunk", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error(`[CHUNK UPLOAD] Error en chunk ${chunkIndex + 1}:`, response.status, errorData);
        } else {
            console.log(`[CHUNK UPLOAD] Chunk ${chunkIndex + 1}/${totalChunks} aceptado por el servidor`);
        }

        return response;
    } catch (err) {
        console.error(`[CHUNK UPLOAD] Error de red en chunk ${chunkIndex + 1}:`, err);
        throw err;
    }
}

/**
 * Notifica al servidor que todos los chunks han sido enviados
 */
async function completeUpload(uploadId, nombre, modo, email) {
    console.log(`[UPLOAD COMPLETE] Notificando servidor para ensamblar (uploadId: ${uploadId})`);

    const formData = new FormData();
    formData.append("uploadId", uploadId);
    formData.append("nombre", nombre);
    formData.append("modo", modo);
    formData.append("email", email);

    try {
        const response = await fetch("/api/upload-complete", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error("[UPLOAD COMPLETE] Error:", response.status, errorData);
        } else {
            console.log("[UPLOAD COMPLETE] Solicitud enviada correctamente");
        }

        return response;
    } catch (err) {
        console.error("[UPLOAD COMPLETE] Error de red:", err);
        throw err;
    }
}

/**
 * Envía un nuevo archivo de audio al servidor en chunks
 */
async function uploadAudio(audioBlob, nombre, modo, email) {
    if (!audioBlob) {
        console.error("[UPLOAD AUDIO] No hay grabación disponible");
        return {
            success: false,
            error: "No hay grabación disponible."
        };
    }

    // Determinar extensión según MIME type
    let extension = "webm";
    if (audioBlob.type.includes("mp4") || audioBlob.type.includes("aac")) {
        extension = "m4a";
    } else if (audioBlob.type.includes("ogg")) {
        extension = "ogg";
    }

    const CHUNK_SIZE = 10 * 1024 * 1024; // 10MB por chunk
    const totalSize = audioBlob.size;
    const totalChunks = Math.ceil(totalSize / CHUNK_SIZE);
    const uploadId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    console.log(`[UPLOAD AUDIO] Iniciando subida:`);
    console.log(`  Nombre: ${nombre}`);
    console.log(`  Tamaño total: ${(totalSize / 1024 / 1024).toFixed(2)} MB`);
    console.log(`  Número de chunks: ${totalChunks}`);
    console.log(`  Upload ID: ${uploadId}`);
    console.log(`  Extensión: .${extension}`);

    setStatusText(`Subiendo audio... (0/${totalChunks} chunks)`);
    showOverlay();

    try {
        // Enviar cada chunk
        for (let i = 0; i < totalChunks; i++) {
            const start = i * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, totalSize);
            const chunk = audioBlob.slice(start, end);

            setStatusText(`Subiendo audio... (${i + 1}/${totalChunks} chunks)`);

            const response = await uploadChunk(chunk, i, totalChunks, uploadId, nombre, modo, email, extension);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Error en chunk ${i + 1}: ${response.status}`);
            }

            console.log(`[UPLOAD AUDIO] Chunk ${i + 1}/${totalChunks} enviado y confirmado`);
        }

        console.log("[UPLOAD AUDIO] Todos los chunks enviados correctamente");

        // Todos los chunks enviados, ensamblar en servidor
        setStatusText("Finalizando subida...");

        const completeResponse = await completeUpload(uploadId, nombre, modo, email);

        console.log("[UPLOAD AUDIO] Respuesta de completado recibida, status:", completeResponse.status);

        if (!completeResponse.ok) {
            const errorData = await completeResponse.json().catch(() => ({}));
            throw new Error(errorData.error || `Error al completar subida: ${completeResponse.status}`);
        }

        const data = await completeResponse.json();
        console.log("[UPLOAD AUDIO] Datos recibidos del servidor:", data);

        if (data.job_id) {
            console.log(`[UPLOAD AUDIO] Job creado exitosamente: ${data.job_id}`);
            return {
                success: true,
                jobId: data.job_id
            };
        } else if (data.error) {
            throw new Error(data.error);
        } else {
            throw new Error("Respuesta del servidor inválida");
        }
    } catch (err) {
        console.error("[UPLOAD AUDIO] Error completo:", err);
        hideOverlay();

        let errorMessage = "Error al enviar el audio.";
        const errMsg = err.message || "";

        if (errMsg.includes("Failed to fetch")) {
            errorMessage = "Error de red. Verifica tu conexión a internet.";
        } else if (errMsg.includes("CORS")) {
            errorMessage = "Error de permisos CORS. Contacta al administrador.";
        } else {
            errorMessage = errMsg;
        }

        console.error("[UPLOAD AUDIO] Error final:", errorMessage);
        return {
            success: false,
            error: errorMessage
        };
    }
}

/**
 * Verifica el estado de un job en el servidor
 */
async function checkJobStatus(jobId) {
    try {
        const res = await fetch(`/api/status/${jobId}`);
        const data = await res.json();
        return data;
    } catch (error) {
        console.error("Error en polling:", error);
        throw error;
    }
}

/**
 * Carga un archivo markdown de resultados
 */
async function loadMarkdownResult(nombre, modo) {
    const normalizedNombre = normalizeText(nombre);
    const normalizedModo = normalizeText(modo);
    const archivoMd = `${normalizedNombre}_${normalizedModo}.md`;

    try {
        const res = await fetch(`/api/resultados/${archivoMd}`);
        if (res.ok) {
            return await res.text();
        }
        return null;
    } catch (e) {
        console.error("Error cargando markdown:", e);
        return null;
    }
}

/**
 * Carga un archivo de transcripción
 */
async function loadTranscriptionFile(nombre) {
    const normalizedNombre = normalizeText(nombre);
    const archivoTxt = `${normalizedNombre}.txt`;

    try {
        const res = await fetch(`/api/transcripciones/${archivoTxt}`);
        if (res.ok) {
            return await res.text();
        }
        return null;
    } catch (e) {
        console.error("Error cargando transcripción:", e);
        return null;
    }
}

/**
 * Stream de chat desde el servidor
 */
async function* chatStream(message, mode, transcripcion, resumen) {
    const payload = {
        message: `Transcripción original:\n${transcripcion}\n\nResultado procesado:\n${resumen}\n\nMi pregunta es:\n${message}`,
        mode: mode
    };

    const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = "";
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        yield chunk;
    }
}

export {
    chatStream, checkJobStatus,
    loadMarkdownResult,
    loadTranscriptionFile, processExistingTranscription,
    uploadAudio
};

