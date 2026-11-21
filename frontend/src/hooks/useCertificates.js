import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "../services/api";
import * as certificateService from "../services/certificateService";

/** Loads the certificate list from the backend and lets the page reload it. */
export function useCertificates({ limit = 200 } = {}) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await certificateService.list({ limit });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { items, total, loading, error, reload };
}