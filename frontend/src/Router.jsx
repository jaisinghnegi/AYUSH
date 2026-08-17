import { BrowserRouter, Routes, Route } from 'react-router-dom';
//import whatever components you want here
import Starter from './components/loader/Starter';
import HomePage from './pages/Home';
import Login from './pages/login/login';
import RegistrationPage from './pages/registration/registration';
import Documentation from './pages/apidocumentation/documentation.jsx';
import Coverage from './pages/coverage/Coverage.jsx';
import Analytics from './pages/analytics/Analytics.jsx';

const Router = () => {
  return (
    <BrowserRouter>
    <Starter/>
      {/* <Navbar />  <-- Navbar here would keep it static for all pages.*/}
      <Routes> 
        <Route index element={<Login />} />
        <Route path="/register" element={<RegistrationPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/docs" element={<Documentation />} />
        <Route path="/coverage" element={<Coverage />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/insights" element={<Analytics />} />
        
        {/* Add your pages in a Route component like these: */}
        {/* 
        <Route index element={<HomePage />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/register" element={<Register />} />
        <Route path="/profile/:id" element={<Profile />} />
        <Route path="/cats" element={<Categories />} /> 
        */}
      </Routes>
    </BrowserRouter>
  );
};

export default Router;
