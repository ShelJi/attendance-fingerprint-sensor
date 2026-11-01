export function simpleError(message: string) {
  const text = message.toLowerCase();
  if (/wi-fi|wifi|ssid|bssid/.test(text)) return 'Connect to the Wi-Fi.';
  if (/outside/.test(text)) return 'Outside office.';
  if (/employee|account/.test(text)) return 'Account unavailable.';
  if (/csrf|authentication|session expired/.test(text)) return 'Sign in again.';
  if (/request failed|not found/.test(text)) return 'Unavailable.';
  if (message.length <= 50 && !/[;_]/.test(message)) return message;
  if (/password/.test(text)) return 'Password not accepted.';
  if (/location|gps|latitude|longitude|accuracy/.test(text)) return 'Location unavailable.';
  if (/notification|push/.test(text)) return 'Notifications unavailable.';
  if (/account|employee profile/.test(text)) return 'Account unavailable.';
  if (/sign in|authentication|session/.test(text)) return 'Sign in again.';
  if (/server|network|connection|reach/.test(text)) return "Can't connect.";
  return 'Unavailable. Try again.';
}
