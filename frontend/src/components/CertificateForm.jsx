import { useState } from "react";

const EMPTY = {
  certificate_id: "",
  student_name: "",
  student_id: "",
  institution_name: "",
  degree: "",
  department: "",
  graduation_year: "",
};

// Synthetic demo data only. Never type real student data into a demo system.
function sampleData() {
  const n = String(Math.floor(Math.random() * 9000) + 1000);
  return {
    certificate_id: `CERT-2026-${n}`,
    student_name: "Asha Raman",
    student_id: `STU${n}`,
    institution_name: "Demo Institute of Technology",
    degree: "B.Tech",
    department: "Computer Science and Engineering",
    graduation_year: "2026",
  };
}

export default function CertificateForm({ onSubmit, submitting, error }) {
  const [form, setForm] = useState(EMPTY);

  function update(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit({ ...form, graduation_year: Number(form.graduation_year) });
  }

  return (
    <form className="card form" onSubmit={handleSubmit}>
      <div className="form-head">
        <h2>Certificate details</h2>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setForm(sampleData())}>
          Fill with sample data
        </button>
      </div>

      <div className="grid-2">
        <label>
          Certificate ID
          <input
            name="certificate_id"
            value={form.certificate_id}
            onChange={update}
            required
            pattern="[A-Za-z0-9][A-Za-z0-9_/\-]{2,63}"
            title="3-64 characters: letters, digits, - _ /"
            placeholder="CERT-2026-0001"
          />
        </label>
        <label>
          Student ID
          <input
            name="student_id"
            value={form.student_id}
            onChange={update}
            required
            pattern="[A-Za-z0-9][A-Za-z0-9_/\-]{0,39}"
            title="Up to 40 characters: letters, digits, - _ /"
            placeholder="STU1001"
          />
        </label>
      </div>

      <label>
        Student name
        <input name="student_name" value={form.student_name} onChange={update} required maxLength={120} />
      </label>
      <label>
        Institution name
        <input name="institution_name" value={form.institution_name} onChange={update} required maxLength={160} />
      </label>

      <div className="grid-2">
        <label>
          Degree / qualification
          <input name="degree" value={form.degree} onChange={update} required maxLength={160} placeholder="B.Tech" />
        </label>
        <label>
          Department / specialization
          <input name="department" value={form.department} onChange={update} required maxLength={160} />
        </label>
      </div>

      <label>
        Graduation year
        <input
          name="graduation_year"
          type="number"
          min="1950"
          max="2100"
          value={form.graduation_year}
          onChange={update}
          required
        />
      </label>

      {error && <div className="alert alert-bad" role="alert">{error}</div>}

      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting ? "Registering on blockchain…" : "Issue certificate"}
      </button>
      <p className="muted small">
        Only a salted hash is written to the blockchain. Names and other details stay in the
        institution's database and in the certificate file given to the student.
      </p>
    </form>
  );
}