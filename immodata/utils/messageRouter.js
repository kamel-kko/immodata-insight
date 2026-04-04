/**
 * ImmoData — Routeur de messages
 * Valide et dispatche les messages entre content script et background.
 *
 * Analogie : c'est comme un standard téléphonique.
 * Un message arrive, on vérifie qu'il a le bon format et qu'il demande
 * une action autorisée, puis on le transmet au bon service.
 * Si l'action est inconnue, on refuse poliment.
 */

import { createLogger } from './logger.js';

const log = createLogger('ROUTER');

// Liste blanche des actions autorisées — tout message avec une action
// qui n'est pas dans cette liste sera rejeté
const ALLOWED_ACTIONS = [
  'SCRAPE_DATA',
  'FETCH_BAN',
  'FETCH_DVF',
  'FETCH_GEORISQUES',
  'FETCH_EDUCATION',
  'FETCH_OVERPASS',
  'FETCH_ADEME',
  'FETCH_LOYERS',
  'FETCH_RTE',
  'FETCH_BRUIT',
  'FETCH_MERIMEE',
  'FETCH_SIRENE',
  'FETCH_ORS',
  'FETCH_ANIL',
  'GET_CACHE',
  'SET_CACHE',
  'CLEAR_CACHE',
  'TRACK_CLICK',
  'OPEN_AFFILIATE_URL'
];

/**
 * Valide un message entrant.
 * Vérifie que :
 * 1. Le message est un objet avec une propriété "action"
 * 2. L'action est dans la liste blanche
 * 3. Le payload (si présent) est un objet simple (pas un tableau, pas null)
 *
 * @param {any} message - Le message reçu
 * @returns {{ valid: boolean, error?: string }}
 */
function validateMessage(message) {
  // Le message doit être un objet non null
  if (!message || typeof message !== 'object' || Array.isArray(message)) {
    return { valid: false, error: 'Message invalide : objet attendu' };
  }

  // L'action doit exister et être une string
  if (typeof message.action !== 'string') {
    return { valid: false, error: 'Message invalide : action manquante' };
  }

  // L'action doit être dans la liste blanche
  if (!ALLOWED_ACTIONS.includes(message.action)) {
    log.warn(`Action non autorisée : "${message.action}"`);
    return { valid: false, error: 'UNAUTHORIZED_ACTION' };
  }

  // Si un payload est fourni, il doit être un objet simple
  if (message.payload !== undefined) {
    if (typeof message.payload !== 'object' || message.payload === null || Array.isArray(message.payload)) {
      return { valid: false, error: 'Payload invalide : objet simple attendu' };
    }
  }

  return { valid: true };
}

/**
 * Crée le dispatcher de messages pour le background.
 * On lui passe un objet "handlers" qui associe chaque action à sa fonction.
 *
 * Exemple :
 *   const dispatch = createDispatcher({
 *     FETCH_BAN: (payload) => fetchBan(payload),
 *     FETCH_DVF: (payload) => fetchDvf(payload),
 *   });
 *
 * @param {Object<string, Function>} handlers - Les fonctions par action
 * @returns {Function} La fonction de dispatch à brancher sur onMessage
 */
function createDispatcher(handlers) {
  return async function dispatch(message, sender, sendResponse) {
    const validation = validateMessage(message);

    if (!validation.valid) {
      log.warn(`Message rejeté : ${validation.error}`);
      sendResponse({
        success: false,
        error: validation.error,
        message: `Action refusée : ${validation.error}`
      });
      return true; // true = on envoie une réponse asynchrone
    }

    const { action, payload } = message;
    const handler = handlers[action];

    if (!handler) {
      // L'action est autorisée mais pas encore implémentée
      log.warn(`Action "${action}" autorisée mais non implémentée`);
      sendResponse({
        success: false,
        error: 'NOT_IMPLEMENTED',
        message: `L'action "${action}" n'est pas encore implémentée`
      });
      return true;
    }

    try {
      log.debug(`Dispatch : ${action}`);
      const result = await handler(payload || {});
      sendResponse({ success: true, ...result });
    } catch (err) {
      log.error(`Erreur dans handler "${action}":`, err);
      sendResponse({
        success: false,
        error: 'HANDLER_ERROR',
        message: err.message || 'Erreur interne'
      });
    }

    return true;
  };
}

if (typeof globalThis.__immodata === 'undefined') {
  globalThis.__immodata = {};
}
globalThis.__immodata.messageRouter = {
  validateMessage,
  createDispatcher,
  ALLOWED_ACTIONS
};

export { validateMessage, createDispatcher, ALLOWED_ACTIONS };
