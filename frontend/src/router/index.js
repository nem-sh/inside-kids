import Vue from "vue";
import VueRouter from "vue-router";

//도연
import KidsDetailView from "@/views/parents/KidsDetailView";
import KidsTalkingView from "@/views/kids/KidsTalkingView";
import KidsPictureView from "@/views/kids/KidsPictureView";
import KidsDrawingView from "@/views/kids/KidsDrawingView";

//수미
import Home from "@/views/Home";
import KidsManageView from "@/views/parents/KidsManageView";
import KidsMainView from "@/views/kids/KidsMainView";
import KidsDrawingListView from "@/views/kids/KidsDrawingListView";
import KidsLoginView from "@/views/kids/KidsLoginView";
import KidsSelectView from "@/views/kids/KidsSelectView";

//시성
import KidMusicView from "@/views/kids/KidMusicView";

Vue.use(VueRouter);

const routes = [
  {
    path: "/",
    name: "Home",
    component: Home,
  },
  {
    path: "/parents/kids/manage",
    name: "KidsManageView",
    component: KidsManageView,
  },
  {
    path: "/child/talking",
    name: "KidsTalkingView",
    component: KidsTalkingView,
  },
  {
    path: "/child/picture",
    name: "KidsPictureView",
    component: KidsPictureView,
  },
  {
    path: "/child/:kidId/drawing",
    name: "KidsDrawingView",
    component: KidsDrawingView,
  },
  {
    path: "/child/:kidId/drawing/list",
    name: "KidsDrawingListView",
    component: KidsDrawingListView,
  },
  {
    path: "/child",
    name: "KidsLoginView",
    component: KidsLoginView,
  },
  {
    path: "/child/select",
    name: "KidsSelectView",
    component: KidsSelectView,
  },
  {
    path: "/child/:kidId",
    name: "KidsMainView",
    component: KidsMainView,
  },
  {
    path: "/child/:kidId/music",
    name: "KidMusicView",
    component: KidMusicView,
  },
  {
    path: "/parents/:kidId",
    name: "KidsDetailView",
    component: KidsDetailView,
  },
];

const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes,
});

router.beforeEach((to, from, next) => {
  // 부모 Login 필수
  const loggedInPagesP = ["KidsManageView", "KidsDetailView"];
  const authRequiredP = loggedInPagesP.includes(to.name);

  // 아이 Login 필수
  const loggedInPagesC = [
    "KidMusicView",
    "KidsDrawingView",
    "KidsDrawingListView",
    "KidsMainView",
    "KidsPictureView",
    "KidsSelectView",
    "KidsTalkingView",
  ];
  const authRequiredC = loggedInPagesC.includes(to.name);

  // Login 되어 있으면 안됨
  const notLoggedInPages = ["KidsLoginView"];
  const unAuthRequired = notLoggedInPages.includes(to.name);

  // Login 판단
  const isLoggedIn = !!Vue.$cookies.isKey("auth-token");

  if (unAuthRequired && isLoggedIn) {
    next(from);
  }
  if (authRequiredP && !isLoggedIn) {
    next("/");
  } else if (authRequiredC && !isLoggedIn) {
    next("/child");
  } else {
    next();
  }
});

export default router;
