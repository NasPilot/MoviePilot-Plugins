<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-h5">
            智能识别词
          </v-card-title>
          <v-card-text>
            <p>增强媒体识别功能，从整理记录中提取识别词。</p>
            <v-divider class="my-4" />
            <v-row>
              <v-col cols="12" md="6">
                <v-list>
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon>mdi-information</v-icon>
                    </template>
                    <v-list-item-title>插件版本</v-list-item-title>
                    <v-list-item-subtitle>1.0.0</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon>mdi-account</v-icon>
                    </template>
                    <v-list-item-title>插件作者</v-list-item-title>
                    <v-list-item-subtitle>
                      <a href="https://github.com/NasPilot" target="_blank" class="text-decoration-none">
                        NasPilot
                      </a>
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-col>
              <v-col cols="12" md="6">
                <v-img
                  src="https://raw.githubusercontent.com/NasPilot/MoviePilot-Plugins/main/icons/identifier.png"
                  max-width="200"
                  class="mx-auto"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
// Page component is mainly for display, no complex logic needed
</script>