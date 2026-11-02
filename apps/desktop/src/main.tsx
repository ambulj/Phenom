import React from 'react';
import ReactDOM from 'react-dom/client';
import { FluentProvider } from '@fluentui/react-components';
import { phenomCyberTheme } from './theme';
import './theme.css';
import App from './App';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <FluentProvider theme={phenomCyberTheme}>
      <App />
    </FluentProvider>
  </React.StrictMode>
);
