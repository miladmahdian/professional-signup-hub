import { apiCall } from './client';

export function fetchProfessionals(source) {
  const params = source ? `?source=${source}` : '';
  return apiCall(`/professionals/${params}`);
}

export function createProfessional(data) {
  return apiCall('/professionals/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
