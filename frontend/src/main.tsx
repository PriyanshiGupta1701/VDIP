import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/index.css'
import App from '@/App.tsx'
import { Provider } from 'react-redux'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css';
import { store } from '@/store'
import { UserProvider } from '@/context/userContext'
import { UsersDataProvider } from '@/context/usersDataContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <UserProvider>
        <UsersDataProvider>
          <ToastContainer
            position='top-right'
            closeOnClick={true}
            autoClose={3000}
          />
          <App />
        </UsersDataProvider>
      </UserProvider>
    </Provider>
  </StrictMode>,
)
