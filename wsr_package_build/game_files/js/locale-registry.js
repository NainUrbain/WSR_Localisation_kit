// Generated from locale_profiles.json. Do not edit.
import { KO_RULES as rules0 } from './lang-ko.js';
import { FR_RULES as rules1 } from './lang-fr.js';
import { JA_RULES as rules2 } from './lang-ja.js';
export const LANGUAGE_RULES = {
    "ko-KR": rules0,
    "fr-FR": rules1,
    "ja-JP": rules2,
};
export const LOCALE_PROFILES = {
  "ko-KR": {
    "data_prefix": "ko"
  },
  "fr-FR": {
    "data_prefix": "fr"
  },
  "ja-JP": {
    "data_prefix": "ja"
  }
};
export function localeDataFile(locale, suffix) {
    const profile = LOCALE_PROFILES[locale];
    return profile ? `${profile.data_prefix}-${suffix}` : null;
}
