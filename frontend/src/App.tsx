import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { UPDATES_PAGE } from './config/navigation';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { AutomationPage } from './pages/AutomationPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsDiscoveryPage } from './pages/JobsDiscoveryPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { PreferencesPage } from './pages/PreferencesPage';
import { ResumesPage } from './pages/ResumesPage';
import { SettingsPage } from './pages/SettingsPage';
import { UpdatesPage } from './pages/UpdatesPage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="/preferences" element={<PreferencesPage />} />
          <Route path="/resume" element={<ResumesPage />} />
          <Route path="/jobs" element={<JobsDiscoveryPage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/automation" element={<AutomationPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path={UPDATES_PAGE.path} element={<UpdatesPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
