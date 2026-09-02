import { Animated, Easing } from "react-native";

export const duration = {
  micro: 140,
  component: 220,
  screen: 320,
};

export function pressIn(value: Animated.Value) {
  Animated.timing(value, {
    toValue: 0.97,
    duration: duration.micro,
    easing: Easing.out(Easing.quad),
    useNativeDriver: true,
  }).start();
}

export function pressOut(value: Animated.Value) {
  Animated.spring(value, {
    toValue: 1,
    friction: 7,
    tension: 140,
    useNativeDriver: true,
  }).start();
}

export function fadeIn(value: Animated.Value, ms = duration.component) {
  Animated.timing(value, {
    toValue: 1,
    duration: ms,
    easing: Easing.out(Easing.cubic),
    useNativeDriver: true,
  }).start();
}
