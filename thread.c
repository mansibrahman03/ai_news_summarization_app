#include <pthread.h>
#include <stdlib.h>

#define MAX_ENTRIES 3

void *func(void *vargp);

typedef struct {
    char* key;
    char* value;
} Entry;

typedef struct {
    Entry arr[MAX_ENTRIES];
} Dict;

typedef struct {
    char* api_key;
    char* category;
    int article_num;
} ArticleInfo;

int main() {
    pthread_t tid;
    ArticleInfo *args = malloc(sizeof(ArticleInfo));
    args->api_key = " ";
    args->category = " ";
    args->article_num = 0;
    pthread_create(&tid, NULL, func, (void*)args);
    pthread_join(tid, NULL);
    free(args);
    return 0;
}

void *func(void *vargp) {
    ArticleInfo *args = (ArticleInfo*) vargp;
    return args;
}