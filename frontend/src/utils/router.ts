// Router utilities for navigation outside of React components

let navigateFunction: ((path: string) => void) | null = null;

export const setNavigate = (navigate: (path: string) => void) => {
  navigateFunction = navigate;
};

export const navigateTo = (path: string) => {
  if (navigateFunction) {
    navigateFunction(path);
  } else {
    // Fallback to window.location if navigate function not set
    // This should rarely happen
    console.warn('Navigate function not set, using window.location');
    window.location.href = path;
  }
};