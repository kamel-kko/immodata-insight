/**
 * ImmoData — Logger centralisé
 * Tous les messages de log passent par ici, jamais de console.log direct.
 *
 * En mode DEV : affiche tout (DEBUG, INFO, WARN, ERROR).
 * En mode PROD : affiche uniquement les ERROR.
 * Format : [ImmoData][MODULE][LEVEL] message
 */

// Flag de développement — mettre à false pour la version publiée
const DEV = true;

const LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3
};

// En prod, seules les erreurs s'affichent
const MIN_LEVEL = DEV ? LEVELS.DEBUG : LEVELS.ERROR;

/**
 * Crée un logger pour un module donné.
 * Comme un carnet de bord étiqueté au nom du module,
 * pour savoir d'où vient chaque message.
 *
 * Exemple : const log = createLogger('SCRAPER');
 *           log.info('Données extraites');
 *           → [ImmoData][SCRAPER][INFO] Données extraites
 */
function createLogger(moduleName) {
  const prefix = `[ImmoData][${moduleName}]`;

  return {
    debug(...args) {
      if (MIN_LEVEL <= LEVELS.DEBUG) {
        console.debug(`${prefix}[DEBUG]`, ...args);
      }
    },
    info(...args) {
      if (MIN_LEVEL <= LEVELS.INFO) {
        console.info(`${prefix}[INFO]`, ...args);
      }
    },
    warn(...args) {
      if (MIN_LEVEL <= LEVELS.WARN) {
        console.warn(`${prefix}[WARN]`, ...args);
      }
    },
    error(...args) {
      if (MIN_LEVEL <= LEVELS.ERROR) {
        console.error(`${prefix}[ERROR]`, ...args);
      }
    }
  };
}

if (typeof globalThis.__immodata === 'undefined') {
  globalThis.__immodata = {};
}
globalThis.__immodata.createLogger = createLogger;
globalThis.__immodata.loggerConfig = { DEV, LEVELS, MIN_LEVEL };

export { createLogger, DEV, LEVELS, MIN_LEVEL };
