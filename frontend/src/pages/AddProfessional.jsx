import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProfessional } from '../api/professionals';

const INITIAL_FORM = {
  full_name: '',
  email: '',
  phone: '',
  company_name: '',
  job_title: '',
  source: '',
};

const SOURCE_OPTIONS = [
  { value: '', label: 'Select source...' },
  { value: 'direct', label: 'Direct' },
  { value: 'partner', label: 'Partner' },
  { value: 'internal', label: 'Internal' },
];

export default function AddProfessional() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [fieldErrors, setFieldErrors] = useState({});

  const mutation = useMutation({
    mutationFn: createProfessional,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['professionals'] });
      navigate('/professionals');
    },
    onError: (error) => {
      if (typeof error === 'object' && error !== null) {
        setFieldErrors(error);
      }
    },
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setFieldErrors({});
    mutation.mutate(formData);
  };

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        Add Professional
      </h2>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Field
          label="Full Name"
          name="full_name"
          value={formData.full_name}
          onChange={handleChange}
          error={fieldErrors.full_name}
          required
        />

        <Field
          label="Email"
          name="email"
          type="email"
          value={formData.email}
          onChange={handleChange}
          error={fieldErrors.email}
        />

        <Field
          label="Phone"
          name="phone"
          value={formData.phone}
          onChange={handleChange}
          error={fieldErrors.phone}
          required
        />

        <Field
          label="Company Name"
          name="company_name"
          value={formData.company_name}
          onChange={handleChange}
          error={fieldErrors.company_name}
        />

        <Field
          label="Job Title"
          name="job_title"
          value={formData.job_title}
          onChange={handleChange}
          error={fieldErrors.job_title}
        />

        <div>
          <label
            htmlFor="source"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Source <span className="text-red-500">*</span>
          </label>
          <select
            id="source"
            name="source"
            value={formData.source}
            onChange={handleChange}
            required
            className={`w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 ${
              fieldErrors.source
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
            }`}
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {fieldErrors.source && (
            <p className="mt-1 text-sm text-red-600">
              {fieldErrors.source[0]}
            </p>
          )}
        </div>

        {fieldErrors.non_field_errors && (
          <p className="text-sm text-red-600">
            {fieldErrors.non_field_errors[0]}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {mutation.isPending ? 'Submitting...' : 'Add Professional'}
        </button>
      </form>
    </div>
  );
}

function Field({ label, name, type = 'text', value, onChange, error, required }) {
  return (
    <div>
      <label
        htmlFor={name}
        className="block text-sm font-medium text-gray-700 mb-1"
      >
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        className={`w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 ${
          error
            ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
            : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
        }`}
      />
      {error && (
        <p className="mt-1 text-sm text-red-600">{error[0]}</p>
      )}
    </div>
  );
}
