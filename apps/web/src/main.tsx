import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { installTestStateBridge } from './state/testStateBridge';

const queryClient = new QueryClient();

if (
  import.meta.env.DEV ||
  import.meta.env.MODE === 'test' ||
  import.meta.env.VITE_GHOSTRANGE_TEST_HOOK === 'true'
) {
  installTestStateBridge();
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
