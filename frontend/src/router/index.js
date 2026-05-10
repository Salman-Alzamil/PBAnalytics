import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Contacts from '../views/Contacts.vue'
import CallHistory from '../views/CallHistory.vue'
import Favourites from '../views/Favourites.vue'
import ImportCSV from '../views/ImportCSV.vue'
import FaceSearch from '../views/FaceSearch.vue'
import ManageContacts from '../views/ManageContacts.vue'
const routes = [
 { path: '/', name: 'Dashboard', component: Dashboard },
 { path: '/contacts', name: 'Contacts', component: Contacts },
 { path: '/calls', name: 'CallHistory', component: CallHistory },
 { path: '/favourites', name: 'Favourites', component: Favourites },
 { path: '/import', name: 'ImportCSV', component: ImportCSV },
 { path: '/face-search', name: 'FaceSearch', component: FaceSearch },
 { path: '/manage', name: 'ManageContacts', component: ManageContacts },
]
const router = createRouter({
 history: createWebHistory(),
 routes,
})
export default router