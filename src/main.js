import {
	createSSRApp
} from "vue";
import App from "./App.vue";
import Varlet from "@varlet/ui";
import "@varlet/ui/es/varlet.css";

export function createApp() {
	const app = createSSRApp(App);
	app.use(Varlet);
	return {
		app,
	};
}
