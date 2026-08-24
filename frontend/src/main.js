import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import axios from "axios";
import "./style.css";
import "./guardian.css";

axios.defaults.withCredentials = true;

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount("#app");
