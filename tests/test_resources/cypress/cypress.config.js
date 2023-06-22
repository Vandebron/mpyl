const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    specPattern: 'dist/specs',
    supportFile: false,
    projectId: '11wp34',
    video: false,
    screenshotOnRunFailure: false
  },
  reporter: 'junit'
});
