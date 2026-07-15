import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate } from "k6/metrics";

const rejected429 = new Counter("bulkhead_rejected_429");
const successful201 = new Counter("reservations_created_201");
const controlledResponses = new Rate("controlled_responses");

export const options = {
  scenarios: {
    request_storm: {
      executor: "constant-vus",
      vus: 30,
      duration: "20s",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<9000"],
    controlled_responses: ["rate>0.95"],
  },
};

const payload = JSON.stringify({
  customer_name: "Prueba Diluvio",
  customer_email: "diluvio@example.com",
  event_id: 1,
  quantity: 1,
});

const params = {
  headers: {
    "Content-Type": "application/json",
  },
  timeout: "10s",
};

export default function () {
  const response = http.post(
    "http://localhost:8080/reservations",
    payload,
    params
  );

  const isCreated = response.status === 201;
  const isRejected = response.status === 429;
  const isControlled =
    response.status === 201 ||
    response.status === 409 ||
    response.status === 429 ||
    response.status === 503 ||
    response.status === 504;

  successful201.add(isCreated ? 1 : 0);
  rejected429.add(isRejected ? 1 : 0);
  controlledResponses.add(isControlled);

  check(response, {
    "respuesta controlada": () => isControlled,
    "respuesta esperada del sistema": () => isControlled,
  });

  sleep(0.1);
}