import * as React from "react";
import { useState, useEffect } from "react";

import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, Button } from 'react-native';

export default function App() {

  const [count, setCount] = useState(0);

  const [pyres, setPyres] = useState("");

  const increment = () => {
    setCount(count + 1)
  }

  useEffect(() => {

  }, []);

  return (
    <View style={styles.container}>
      <Text>Open up App.js to start working on your app! {count}</Text>
      <Button onPress={increment} title="Increment" />
      <Text>Here: {pyres}</Text>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
