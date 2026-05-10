import axios from 'axios'

const http = axios.create({

  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',

})

export const api = {

  getContacts: (params) => http.get('/contacts', { params }),

  getContact: (id) => http.get(`/contacts/${id}`),

  createContact: (data) => http.post('/contacts', data),

  updateContact: (id, data) => http.put(`/contacts/${id}`, data),

  deleteContact: (id) => http.delete(`/contacts/${id}`),

  updateContactPicture: (id, profile_picture_id) => http.patch(`/contacts/${id}/picture`, { profile_picture_id }),

  deleteContactPicture: (id) => http.delete(`/contacts/${id}/picture`),

  getDuplicates: () => http.get('/contacts/duplicates'),

  getCalls: (params) => http.get('/calls', { params }),

  getStats: () => http.get('/calls/stats'),

  getFavourites: (mode = 'most_called', limit = 10) =>

    http.get('/favourites', { params: { mode, limit } }),

  getSummary: () => http.get('/dashboard/summary'),

  importContacts: (file) => {

    const fd = new FormData()

    fd.append('file', file)

    return http.post('/import/contacts', fd)

  },

  importCalls: (file) => {

    const fd = new FormData()

    fd.append('file', file)

    return http.post('/import/calls', fd)

  },

  classifyImage: (file) => {

    const fd = new FormData()

    fd.append('file', file)

    return http.post('/ai/classify', fd)

  },

  uploadContactPicture: (contactId, file) => {

    const fd = new FormData()

    fd.append('file', file)

    return http.post(`/contacts/${contactId}/picture/upload`, fd)

  },

  searchByFace: (file) => {

    const fd = new FormData()

    fd.append('file', file)

    return http.post('/search/by-face', fd)

  },

  analyzeGroupImage: (file) => {

    const fd = new FormData()

    fd.append('file', file)

    return http.post('/analyze/group-image', fd)

  },

  identifyFace: (embedding) => http.post('/identify/face', { embedding }),

  precomputeFaceEmbeddings: () => http.post('/face-embeddings/precompute'),

  faceIndexStatus: () => http.get('/face-embeddings/status'),

}
 